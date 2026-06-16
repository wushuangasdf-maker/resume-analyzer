"""
FastAPI 简历分析服务 — 完整流水线
===================================
启动方式: uvicorn app.api.main:app --reload

端点:
  GET  /          — 服务信息
  GET  /ping      — 健康检查
  POST /analyze   — 上传简历 + 可选 JD，执行完整分析流水线
"""

import logging
import os
import traceback
from typing import Optional

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.parsers.file_router import parse_resume
from app.services.pipeline import run_analysis_pipeline
from app.services.resume_analyzer import analyze_resume_v2
from app.utils.upload import (
    MAX_FILE_SIZE,
    validate_extension,
    secure_filename,
)

# ---------------------------------------------------------------------------
# 安全配置
# ---------------------------------------------------------------------------
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")

# ---------------------------------------------------------------------------
# 应用实例
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Resume Analyzer",
    description="上传简历（必选）和 JD（可选），返回 AI 分析结果",
    version="2.0.0",
)

# CORS — 仅允许可配置的来源（默认本地 Streamlit），不允许泛 *
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
    """安全保存上传文件：扩展名校验 + 大小校验（流式） + 文件名清洗，返回绝对路径。"""
    original_name = upload.filename or "upload.tmp"

    # 1. 扩展名校验（委托 upload 模块）
    validate_extension(original_name)

    # 2. 安全文件名（防路径遍历）
    safe_name = secure_filename(original_name)
    dest = os.path.join(UPLOAD_DIR, safe_name)

    # 3. 流式写入 + 硬大小限制
    written = 0
    with open(dest, "wb") as f:
        while chunk := upload.file.read(8192):
            written += len(chunk)
            if written > MAX_FILE_SIZE:
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
    4. 加权匹配度评分
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

        # ---- 3. 分析流水线 ---------------------------------------------------
        pipeline_result = run_analysis_pipeline(resume_text, jd_text)
        intermediate = pipeline_result["intermediate"]

        # ---- 4. 终局 AI 分析 -------------------------------------------------
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
