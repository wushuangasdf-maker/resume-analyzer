"""上传文件安全工具 — api 和 web 模块共用。

提供统一的文件类型校验、大小限制、文件名清洗和磁盘写入逻辑，
避免安全策略在多个模块中重复定义导致不一致。
"""

import logging
import os
import re
import uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 安全常量（全局唯一，避免 api/web 各自定义导致不一致）
# ---------------------------------------------------------------------------
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}


# ---------------------------------------------------------------------------
# 校验函数
# ---------------------------------------------------------------------------

def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否在白名单中（大小写不敏感）。"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def validate_extension(filename: str) -> None:
    """校验扩展名，不在白名单则抛出 ValueError。"""
    if not allowed_file(filename):
        ext = os.path.splitext(filename)[1]
        raise ValueError(f"不支持的文件类型: {ext}")


def validate_file_size(size: int) -> None:
    """校验文件大小，超限则抛出 ValueError。"""
    if size > MAX_FILE_SIZE:
        raise ValueError(f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)")


# ---------------------------------------------------------------------------
# 文件名清洗
# ---------------------------------------------------------------------------

def secure_filename(filename: str) -> str:
    """清洗文件名，防止路径遍历攻击。

    规则：取 basename → 移除非安全字符 → 防空名 → 加随机前缀。
    """
    basename = os.path.basename(filename)
    basename = re.sub(r"[^\w一-鿿.\-() ]", "_", basename)
    if not basename or basename.startswith("."):
        basename = "upload.tmp"
    name, ext = os.path.splitext(basename)
    return f"{name}_{uuid.uuid4().hex[:8]}{ext}"


# ---------------------------------------------------------------------------
# 一站式保存（适用于已将文件内容读入 bytes 的场景，如 Streamlit）
# ---------------------------------------------------------------------------

def save_upload(data: bytes, original_name: str, dest_dir: str) -> str:
    """安全保存上传文件到磁盘，返回绝对路径。

    执行顺序：大小校验 → 扩展名校验 → 安全文件名 → 写入磁盘。
    对于大文件流式写入场景（FastAPI），建议自行处理 I/O 并复用上面的校验函数。
    """
    validate_file_size(len(data))
    validate_extension(original_name)

    safe_name = secure_filename(original_name)
    dest = os.path.join(dest_dir, safe_name)

    os.makedirs(dest_dir, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)

    logger.info("文件已安全保存: %s → %s (%d bytes)", original_name, safe_name, len(data))
    return dest
