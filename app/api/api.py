"""旧版 API 端点 — 保留兼容，建议使用 app.api.main"""
import logging
import os
import re
import shutil
import uuid

from fastapi import APIRouter, File, UploadFile

from app.parsers import file_router
from app.services import resume_analyzer

router = APIRouter()

# ---------------------------------------------------------------------------
# 安全配置（与 main.py 保持一致）
# ---------------------------------------------------------------------------
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _secure_filename(filename: str) -> str:
    basename = os.path.basename(filename)
    basename = re.sub(r"[^\w一-鿿.\-() ]", "_", basename)
    if not basename or basename.startswith("."):
        basename = "upload.tmp"
    name, ext = os.path.splitext(basename)
    return f"{name}_{uuid.uuid4().hex[:8]}{ext}"


def _allowed_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------
@router.get("/ping")
def ping():
    return {"message": "ping"}


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        logging.info("收到文件上传请求")

        # ---- 安全校验 ----
        original_name = file.filename or "upload.tmp"
        if not _allowed_file(original_name):
            return {"code": 400, "message": "不支持的文件类型", "data": None}

        safe_name = _secure_filename(original_name)
        file_path = os.path.join(UPLOAD_DIR, safe_name)

        # ---- 流式保存 + 大小限制 ----
        written = 0
        with open(file_path, "wb") as buffer:
            while chunk := file.file.read(8192):
                written += len(chunk)
                if written > MAX_FILE_SIZE:
                    buffer.close()
                    os.remove(file_path)
                    return {"code": 400, "message": "文件大小超过限制", "data": None}
                buffer.write(chunk)

        logging.info("文件已安全保存: %s → %s (%d bytes)", original_name, safe_name, written)

        # ---- 解析简历 ----
        text = file_router.parse_resume(file_path)
        if not text:
            return {"code": 400, "message": "简历内容为空", "data": None}

        logging.info("解析完毕，文本长度: %d", len(text))

        # ---- AI 分析 ----
        logging.info("进行 AI 分析")
        result = resume_analyzer.analyze_resume_v2(text)
        logging.info("AI 分析完毕")

        return {
            "code": 200,
            "message": "success",
            "data": {"filename": original_name, "analysis": result},
        }

    except ValueError:
        return {"code": 400, "message": "请求参数有误", "data": None}
    except Exception:
        logging.exception("分析过程发生异常")
        return {"code": 500, "message": "服务器内部错误", "data": None}