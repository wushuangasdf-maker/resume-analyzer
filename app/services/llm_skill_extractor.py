import json
from app.services.llm_service import chat
from app.utils.json_utils import safe_json_loads, clean_json

def llm_extract_skills(text):
    prompt =f"""
    从以下文本中提取所有技术技能和可能是技能的信息。
    要求：
    1. 仅返回 JSON 数组。
    2. 每项必须是字符串。
    3. 包含编程语言、框架、数据库、工具、云平台。
    4. 不要返回任何解释。
    5. 不要使用 markdown 代码块。

    text:
    {text}
    """
    try:
        responses = chat(prompt)
        if not responses:
            return []
        # 统一使用 safe_json_loads，避免 LLM 返回 markdown 包裹时直接炸
        skills = safe_json_loads(responses)
        if isinstance(skills, list):
            return skills
        # 如果 LLM 返回的是 {"skills": [...]} 格式，尝试提取
        if isinstance(skills, dict):
            for val in skills.values():
                if isinstance(val, list):
                    return val
    except Exception as e:
        print("技能兜底提取失败", e)
    return []