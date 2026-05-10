import json

from app.services.llm_service import chat
from app.config.skill_alias import skill_alias
from app.utils.skill_cache import load_cache,save_cache
from app.utils.json_utils import safe_json_loads


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
   if not  unkonw_skill:
       return {}
   normalized_input=[]
   for skill in unkonw_skill:
       if skill and skill.strip():
           normalized_input.append(skill.lower().strip())
   if not normalized_input:
       return {}
   cache=load_cache()
   results={}
   uncached_skills=[]
   for skill in normalized_input:
       if skill in cache:
           results[skill]= cache[skill]
       else:
           uncached_skills.append(skill)
   if not uncached_skills:
       return results
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
       response=cache(prompt).strip()
       fallback={skill:skill for skill in unkonw_skill}
       ai_result=safe_json_loads(response,fallback=fallback)
       for original,normalized in ai_result.items():
           normalized_value=str(normalized).lower().strip()
           cache[original] = normalized_value
           results[original] = normalized_value
       save_cache(cache)
   except Exception:
       for skill in unkonw_skill:
           results[skill]=skill
   return  results

def normalize_integrate_skill(skills):
    local_skills,unknown_skills=normalize_local_skill(skills)
    ai_skills =[]
    for skill in unknown_skills:
        ai_result=normalize_ai_skill(skill)
        ai_skills.append(ai_result)
    final_skills=set(local_skills+ai_skills)
    return list(final_skills)