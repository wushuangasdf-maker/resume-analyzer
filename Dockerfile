# ============================================================
# AI 简历分析器 — Docker 镜像（安全加固版）
# ============================================================
FROM python:3.11-slim

# ---- 系统依赖 ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    # 安全相关
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---- 创建非 root 用户 ----
RUN groupadd -r appuser && useradd -r -g appuser -m -s /bin/bash appuser

WORKDIR /app

# ---- 依赖安装（利用缓存层）----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- 复制代码 ----
COPY . .

# ---- 创建数据目录并设权限 ----
RUN mkdir -p /app/uploads /app/logs && \
    chown -R appuser:appuser /app

# ---- 切换到非 root 用户 ----
USER appuser

# ---- 暴露端口 ----
EXPOSE 8000 8501

# ---- Python 安全配置 ----
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 默认启动
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]