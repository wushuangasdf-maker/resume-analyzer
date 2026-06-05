from app.config.skill_pool import skill_keywords
from app.services.llm_skill_extractor import llm_extract_skills
from app.services.skill_normalizer import normalize_integrate_skill
from app.utils.decorators import trace
from app.utils.json_utils import safe_json_loads

# skill_keywords 已统一为小写，这里直接构建 set 加速查找
_SKILL_SET = {s.lower().strip() for s in skill_keywords}


@trace
def extract_keywords(text):
    """
    兜底技能提取：LLM 提取 → 归一化 → skill_keywords 过滤。

    注意：归一化后的技能全部为小写，skill_keywords 也已统一小写，
    因此过滤时两边都 .lower() 确保兼容。
    """
    raw_skills = llm_extract_skills(text)
    # llm_extract_skills 已返回解析好的 list，只有非 list 才尝试 JSON 解析
    if not isinstance(raw_skills, list):
        raw_skills = safe_json_loads(raw_skills, fallback=[])
    if not raw_skills:
        return []

    normalized = normalize_integrate_skill(raw_skills)

    # 归一化后全部为小写，与 _SKILL_SET 直接比较
    filtered = [s for s in normalized if s.lower().strip() in _SKILL_SET]

    if not filtered:
        # 宽松兜底：如果全部被过滤，说明关键词库可能缺了这些技能，
        # 直接返回归一化后的结果（去重），避免空返回。
        return sorted(set(normalized))

    return sorted(set(filtered))