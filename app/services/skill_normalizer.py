import json

from app.services.llm_service import chat
from app.config.skill_alias import skill_alias
from app.utils.skill_cache import load_cache,save_cache
from app.utils.json_utils import safe_json_loads
from app.utils.tracer import trace


@trace
def normalize_local_skill(skills):
    if not  skills:
        return [],[]
    local_normal = set()
    unknow = []
    for skill in skills:
        key = skill.lower().strip()
        if key in skill_alias:
            local_normal.add(skill_alias[key])
        else:
            unknow.append(skill)
    return  list(local_normal),unknow

@trace
def normalize_ai_skill(unkonw_skill):
   if not unkonw_skill:
       return []
   normalized_input=[
       s.lower().strip()
       for s in unkonw_skill
       if s and s.strip()
   ]
   if not normalized_input:
       return []
   cache = load_cache() or {}
   results = {}
   uncached_skills = []
   for skill in normalized_input:
       if skill in cache:
           results[skill]= cache[skill]
       else:
           uncached_skills.append(skill)
   if not uncached_skills:
       return list(results.values())
   prompt = f"""
   请将以下技术技能名称标准化，并返回 JSON 对象。

   示例：
   {{
     "torch": "pytorch",
     "js": "javascript",
     "tf": "tensorflow"
   }}

   要求：
   1. key 为原技能名
   2. value 为标准技能名
   3. 无法确定时保持原样
   4. 全部使用小写
   5. 只返回 JSON
   6. 不要使用 markdown 代码块

   技能列表：
   {json.dumps(uncached_skills,ensure_ascii=False)}
   """
   try:
       response=chat(prompt)
       response = (response or "").strip()
       fallback={skill:skill for skill in uncached_skills}
       ai_result=safe_json_loads(response,fallback=fallback)
       if isinstance(ai_result, dict):
           for k, v in ai_result.items():
               v = str(v).lower().strip()
               cache[k] = v
               results[k] = v
       save_cache(cache)
   except Exception:
       for skill in uncached_skills:
           results[skill]=skill
   return  list(results.values())

@trace
def normalize_integrate_skill(skills):
    skills = skills or []

    local_skills,unknown_skills=normalize_local_skill(skills)
    ai_mapping =normalize_ai_skill(unknown_skills)or {}
    if not isinstance(ai_mapping, dict):
        ai_mapping = {}
    ai_skills = [
        str(v).strip().lower()
        for v in ai_mapping.values()
        if v
    ]
    local_skills = local_skills or []
    final_skills=set(local_skills+ai_skills)
    return list(final_skills)