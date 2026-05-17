import re
from app.config.skill_pool import skill_keywords
from app.services.llm_skill_extractor import llm_extract_skills
from app.services.skill_normalizer import normalize_integrate_skill
from app.utils.tracer import trace
#经行文本技能的提取，根据Skill_keywords经行提取（目前情况
@trace
def extract_keywords(text):
    raw_skills=llm_extract_skills(text)
    if not raw_skills:
        return []
    normalized=normalize_integrate_skill(raw_skills)
    filtered=[skill for  skill in normalized if skill in skill_keywords]
    return sorted(set(filtered))