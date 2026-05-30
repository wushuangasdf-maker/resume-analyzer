import json
import re
import logging

logger = logging.getLogger(__name__)

def clean_json(text):
    if not text:
        return ""
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    match = re.search(r"\{.*\}",text)
    if match:
        return match.group().strip()
    return ""

def safe_json_loads(response,fallback=None):
    if fallback is None:
        fallback={}
    try:
        cleaned = clean_json(response)
        if not cleaned:
            logger.warning("JSON clean failed")
            return fallback
        data = json.loads(cleaned)
        if isinstance(data,dict):
            return data
        logger.warning("JSON is not dict")
        return fallback
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error:{e}")
        logger.warning(f"Response:{response}")
        return fallback
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return fallback
