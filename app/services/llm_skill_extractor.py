import json
from http.client import responses

from app.services.llm_service import chat

def llm_extract_skills(text):
    prompt =f"""
    从以下文本中提取所有技术技能。
    要求：
    仅返回一个 JSON 数组。
    包含编程语言、框架、工具、数据库和云平台。
    不要包含任何解释。
    text:
    {text}
    """
    responses =chat(prompt)
    try:
        skills=json.loads(responses)
        if isinstance(skills,list):
            return skills
    except Exception:
        pass
    return []