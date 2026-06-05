import json
from app.services.llm_service import chat
from app.utils.json_utils import safe_json_loads
from app.config.skill_pool import SKILL_POOL_DISPLAY

def llm_extract_skills(text):
    prompt = f"""
    从以下简历文本中提取该候选人**实际具备**的技术技能。

    重要原则：只提取简历中明确提到或强烈暗示的技能，绝不编造。
    技能库仅用于参考标准写法，不是提取清单。

    技能库（仅用于标准化名称）：
    {SKILL_POOL_DISPLAY[:1500]}

    要求：
    1. 仅返回 JSON 数组，每项为技能名称字符串。
    2. 技能名称尽量使用参考库中的标准写法。
    3. 包含但不限于：编程语言、前端/后端框架、数据库、DevOps、云平台、AI/数据科学工具。
    4. 从项目经验、工作经历中也要提取用到的技能。
    5. 不要返回任何解释或 markdown 代码块。

    简历文本:
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