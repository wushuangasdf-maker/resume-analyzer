"""
FastAPI 简历分析服务 — 完整流水线
===================================
启动方式: uvicorn app.api.main:app --reload

端点:
  GET  /          — 服务信息
  GET  /ping      — 健康检查
  POST /analyze   — 上传简历 + 可选 JD，执行完整分析流水线
"""

import json
import logging
import os
import re
import shutil
import tempfile
import traceback
import uuid
from typing import Optional

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.parsers.file_router import parse_resume
from app.services.llm_analyze import llm_analyze
from app.services.resume_analyzer import analyze_resume_v2
from app.services.skill_extractor import extract_keywords
from app.services.skill_match import final_score, skills_report
from app.services.skill_normalizer import normalize_integrate_skill

# ---------------------------------------------------------------------------
# 安全配置
# ---------------------------------------------------------------------------
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB 上传限制
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
# 仅内网/本地部署使用，公网请改为具体域名
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")


def _secure_filename(filename: str) -> str:
    """清洗文件名，防止路径遍历攻击。"""
    # 取最后一段作为文件名，丢弃路径部分
    basename = os.path.basename(filename)
    # 移除非字母数字中文和 . _ - 之外的字符
    basename = re.sub(r"[^\w一-鿿.\-() ]", "_", basename)
    # 防止空文件名或只有扩展名
    if not basename or basename.startswith("."):
        basename = "upload.tmp"
    # 加随机前缀防止冲突
    name, ext = os.path.splitext(basename)
    return f"{name}_{uuid.uuid4().hex[:8]}{ext}"


def _allowed_file(filename: str) -> bool:
    """检查文件扩展名是否在白名单中。"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def _validate_file_size(upload: UploadFile) -> None:
    """检查文件大小是否超限（通过读取内容判断，非 Content-Length）。"""
    # 先检查 Content-Length 头（快速拒绝）
    # FastAPI UploadFile 没有直接暴露 headers，我们从底层 starlette 对象获取
    content_length = upload.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_FILE_SIZE:
                raise ValueError(f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)")
        except ValueError:
            pass  # content-length 不是整数，跳过

# ---------------------------------------------------------------------------
# 应用实例
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Resume Analyzer",
    description="上传简历（必选）和 JD（可选），返回 AI 分析结果",
    version="2.0.0",
)

# CORS — 仅允许可配置的来源（默认本地 Streamlit），不允泛 *
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# 上传文件暂存目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def _save_upload(upload: UploadFile) -> str:
    """安全保存上传文件：清洗文件名 + 大小校验 + 类型校验，返回绝对路径。"""
    original_name = upload.filename or "upload.tmp"

    # 1. 扩展名校验
    if not _allowed_file(original_name):
        raise ValueError(f"不支持的文件类型: {os.path.splitext(original_name)[1]}")

    # 2. 大小校验
    _validate_file_size(upload)

    # 3. 安全文件名（防路径遍历）
    safe_name = _secure_filename(original_name)
    dest = os.path.join(UPLOAD_DIR, safe_name)

    # 4. 流式写入 + 硬大小限制
    written = 0
    with open(dest, "wb") as f:
        while chunk := upload.file.read(8192):
            written += len(chunk)
            if written > MAX_FILE_SIZE:
                f.close()
                os.remove(dest)
                raise ValueError(f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)")
            f.write(chunk)

    logging.info("文件已安全保存: %s → %s (%d bytes)", original_name, safe_name, written)
    return dest


def _safe_parse(path: str) -> Optional[str]:
    """安全解析文件，失败时返回 None 并记录日志。"""
    try:
        text = parse_resume(path)
        if text:
            logging.info("解析成功，文本长度: %d", len(text))
        else:
            logging.warning("解析结果为空: %s", path)
        return text
    except Exception:
        logging.error("解析文件失败: %s\n%s", path, traceback.format_exc())
        return None


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """服务信息"""
    return {
        "service": "AI Resume Analyzer",
        "version": "2.0.0",
        "endpoints": {
            "GET /ping": "健康检查",
            "POST /analyze": "上传简历 (file) + 可选 JD (jd_file)，返回完整分析",
        },
    }


@app.get("/ping")
async def ping():
    """健康检查"""
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(..., description="简历文件 (PDF / DOCX / 图片)"),
    jd_file: Optional[UploadFile] = File(None, description="JD 文件（可选）"),
):
    """
    完整简历分析流水线：

    1. 解析简历 & JD 文本
    2. LLM 结构化抽取（技能 / 项目 / 教育 / 经验 / 建议）
    3. 技能归一化（本地别名 + AI 缓存）
    4. 加权匹配度评分（技能权重 70% + 核心覆盖率 20% - 缺失惩罚 10%）
    5. 终局 AI 分析（评分 / 优劣势 / 推荐岗位 / 提升建议）
    """
    resume_path: Optional[str] = None
    jd_path: Optional[str] = None

    try:
        # ---- 1. 保存上传文件 -------------------------------------------------
        logging.info("收到分析请求: resume=%s, jd=%s",
                      file.filename,
                      jd_file.filename if jd_file else "无")

        resume_path = _save_upload(file)
        if jd_file:
            jd_path = _save_upload(jd_file)

        # ---- 2. 解析文件文本 -------------------------------------------------
        resume_text = _safe_parse(resume_path)
        if not resume_text:
            return {"code": 400, "message": "简历内容为空或解析失败", "data": None}

        jd_text = _safe_parse(jd_path) if jd_path else None

        # ---- 3. LLM 结构化抽取（一次调用） ------------------------------------
        logging.info("开始 LLM 结构化抽取")
        data = llm_analyze(resume_text, jd_text)
        if not isinstance(data, dict):
            logging.warning("llm_analyze 返回异常类型，使用空字典兜底")
            data = {}

        # ---- 4. 兜底：LLM 没抽出技能时用本地规则提取 -------------------------
        if not data.get("skills"):
            data["skills"] = extract_keywords(resume_text)
        if not data.get("jd_skills") and jd_text:
            data["jd_skills"] = extract_keywords(jd_text)

        # ---- 5. 技能归一化 ---------------------------------------------------
        skills = normalize_integrate_skill(data.get("skills") or [])
        jd_skills = normalize_integrate_skill(data.get("jd_skills") or [])

        # ---- 6. 技能匹配 & 评分 ----------------------------------------------
        if jd_skills:
            match, miss, extra = skills_report(skills, jd_skills)
            score = final_score(skills, jd_skills, miss)
        else:
            match, miss, extra = [], [], []
            score = None

        # ---- 7. 组装中间结果 -------------------------------------------------
        intermediate = {
            "skills": skills,
            "projects": data.get("projects") or [],
            "jd_skills": jd_skills,
            "score": score,
            "match": match,
            "missing": miss,
            "extra": extra,
            "summary": data.get("summary", " ") or " ",
        }

        # ---- 8. 终局 AI 分析 -------------------------------------------------
        logging.info("开始终局 AI 分析")
        result = analyze_resume_v2(intermediate)
        logging.info("分析完成")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "filename": file.filename,
                "jd_filename": jd_file.filename if jd_file else None,
                "analysis": result,
            },
        }

    except ValueError as e:
        # 客户端错误（如文件类型/大小不对）
        logging.warning("客户端错误: %s", e)
        return {"code": 400, "message": str(e), "data": None}
    except Exception:
        logging.error("分析流水线异常:\n%s", traceback.format_exc())
        return {"code": 500, "message": "服务器内部错误，请联系管理员", "data": None}

    finally:
        # ---- 清理临时文件 ----------------------------------------------------
        for p in (resume_path, jd_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass