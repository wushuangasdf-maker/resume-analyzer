import json
import re
import logging

logger = logging.getLogger(__name__)

def _extract_balanced(text, open_char, close_char):
    """提取第一个完整的花括号/方括号块，正确处理嵌套。"""
    start = text.find(open_char)
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def clean_json(text):
    if not text:
        return ""
    if not isinstance(text, str):
        if isinstance(text, (dict, list)):
            # 用 json.dumps 保真转换，避免 str() 产生单引号 Python repr
            text = json.dumps(text, ensure_ascii=False)
        else:
            text = str(text)

    # 1️⃣ 优先提取 ```json ... ```
    match = re.search(r"```json\s*(.*?)```", text, re.S)
    if match:
        inner = match.group(1).strip()
        # 从 code block 内部提取 JSON 对象/数组
        obj = _extract_balanced(inner, '{', '}')
        if obj:
            return obj
        arr = _extract_balanced(inner, '[', ']')
        if arr:
            return arr
        return inner

    # 2️⃣ 再提取普通 ``` ... ```
    match = re.search(r"```\s*(.*?)```", text, re.S)
    if match:
        inner = match.group(1).strip()
        obj = _extract_balanced(inner, '{', '}')
        if obj:
            return obj
        arr = _extract_balanced(inner, '[', ']')
        if arr:
            return arr
        return inner

    # 3️⃣ 用括号计数提取完整 JSON 对象（正确处理嵌套）
    obj = _extract_balanced(text, '{', '}')
    if obj:
        return obj.strip()

    # 4️⃣ 尝试匹配 JSON 数组
    arr = _extract_balanced(text, '[', ']')
    if arr:
        return arr.strip()

    # 5️⃣ debug 信息
    logger.warning("JSON clean failed raw output: %s", repr(text))

    return ""

def safe_json_loads(response, fallback=None):
    """安全解析 JSON 字符串，返回 dict / list / fallback。

    修复：之前仅接受 dict，导致 LLM 返回的 JSON 数组（如技能列表）
    被错误丢弃。现在同时接受 dict 和 list。
    """
    if fallback is None:
        fallback = {}
    try:
        cleaned = clean_json(response)
        if not cleaned:
            logger.warning("JSON clean failed")
            return fallback
        data = json.loads(cleaned)
        if isinstance(data, (dict, list)):
            return data
        logger.warning("JSON is not dict or list, got: %s", type(data).__name__)
        return fallback
    except json.JSONDecodeError as e:
        logger.warning("JSON decode error: %s", e)
        logger.warning("Response: %s", response)
        return fallback
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return fallback
