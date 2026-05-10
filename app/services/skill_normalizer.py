from app.services.llm_service import chat
from app.config.skill_alias import skill_alias
from app.utils.skill_cache import load_cache,save_cache


def normalize_local_skill(skills):
    local_normal = set()
    unknow = []
    for skill in skills:
        key = skill.lower().strip()
        if key in skill_alias:
            local_normal.add(skill_alias[key])
        else:
            unknow.append(skill)
    return  list(local_normal),unknow

def normalize_ai_skill(unkonw_skill):
    unkonw_skill = unkonw_skill.lower().strip()
    cache =load_cache()
    if unkonw_skill in cache:
        return cache[unkonw_skill]

    prompt=f"""
    请标准化以下技术技能名称。

    例如：
    torch -> PyTorch
    js -> JavaScript

    技能：
    {unkonw_skill}

    要求：
    1. 只返回标准技能名
    2. 不要解释
    3. 不要代码块
    """
    try:
        result=chat(prompt).strip().lower()
        cache[unkonw_skill]=result
        save_cache(cache)
        return result
    except Exception:
        return unkonw_skill.lower()

def normalize_integrate_skill(skills):
    local_skills,unknown_skills=normalize_local_skill(skills)
    ai_skills =[]
    for skill in unknown_skills:
        ai_result=normalize_ai_skill(skill)
        ai_skills.append(ai_result)
    final_skills=set(local_skills+ai_skills)
    return list(final_skills)