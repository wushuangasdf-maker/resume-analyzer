import json
from app.services.llm_service import chat

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
        responses =chat(prompt)
        if not  responses:
            return []
        skills = json.loads(responses)
        if isinstance(skills,list):
            return skills
    except Exception as e:
        print("技能兜底提取失败",e)
    return []