import logging
import time
import os

from openai import (
    APIError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 客户端初始化
# ---------------------------------------------------------------------------
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    raise ValueError("未找到 API_KEY，请去检查 .env 文件")

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.deepseek.com/v1",
    timeout=60,
)

# ---------------------------------------------------------------------------
# 重试配置
# ---------------------------------------------------------------------------
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # 指数退避基数（秒）：1.5 → 2.25 → 3.375

# 可重试的错误类型：网络问题 / 超时 / 限流 / 服务端 5xx
RETRYABLE_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)


def _is_retryable(error: Exception) -> bool:
    """判断异常是否可重试。

    可重试：连接错误、超时、429 限流、500+ 服务端错误。
    不可重试：400 参数错误、401 认证失败等（重试无意义，直接抛出）。
    """
    if isinstance(error, RETRYABLE_ERRORS):
        return True
    # 某些 SDK 版本把 429/5xx 包装为普通 APIError，需检查 HTTP 状态码
    if isinstance(error, APIError):
        status = getattr(error, "status_code", None) or getattr(error, "http_status", None)
        if status is not None and (status == 429 or status >= 500):
            return True
    return False


def _retry_sleep(attempt: int) -> None:
    """指数退避：1.5s → 2.25s → 3.375s"""
    delay = RETRY_BACKOFF_BASE ** (attempt + 1)
    logger.warning("LLM 调用失败，第 %d 次重试，等待 %.1fs...", attempt + 1, delay)
    time.sleep(delay)


# ---------------------------------------------------------------------------
# 非流式调用
# ---------------------------------------------------------------------------
def chat(prompt):
    """调用 LLM 并返回完整响应，含自动重试。"""
    if not prompt or not prompt.strip():
        return ""

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES and _is_retryable(e):
                _retry_sleep(attempt)
                continue
            # 不可重试 或 已达最大重试次数
            logger.error("LLM 调用失败（attempt %d/%d）：%s", attempt + 1, MAX_RETRIES + 1, e)
            raise

    # 理论不可达，但兜底
    raise last_error  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 流式调用
# ---------------------------------------------------------------------------
def chat_stream(prompt):
    """流式调用 LLM，逐 token 返回文本块，含自动重试。

    注意：流式请求的重试语义不同于非流式——连接建立后开始产出 token 时
    若中断，已产出的数据已发送给调用方，无法回退。因此仅在连接建立阶段重试。
    """
    if not prompt or not prompt.strip():
        yield ""
        return

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                stream=True,
            )
            # 连接已建立，开始消费流
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
            return  # 正常完成
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES and _is_retryable(e):
                _retry_sleep(attempt)
                continue
            logger.error("LLM 流式调用失败（attempt %d/%d）：%s", attempt + 1, MAX_RETRIES + 1, e)
            yield "\n\n> ⚠️ AI 服务暂时不可用，请稍后重试"
            return

    yield "\n\n> ⚠️ AI 服务暂时不可用，请稍后重试"