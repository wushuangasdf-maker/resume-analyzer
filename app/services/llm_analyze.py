from  app.services.llm_service import chat
import json
from app.services.project_extractor import extract_projects
from app.utils.json_utils import safe_json_loads,clean_json
#用于文本的整理，让ai更加精确的发挥
def llm_analyze(user_text,jd_text=None):
  try:
    prompt = f"""
     你是一个JSON生成器。
    必须严格返回合法JSON，不能包含任何解释、代码块或多余文本。
    格式如下：
        {{
        "skills": [],
        "jd_skills":[],
        "missing_skills": [],
        "extra_skills": [],
        "projects": [],
        "education": "",
        "experience": "",
        "score": 0
        }}
        resume:
        {user_text}
        
    """
    if jd_text:
        prompt +=f"\n岗位描述:\n{jd_text}"
    result = chat(prompt)
    fallback = {
        "skills": [],
        "jd_skills": [],
        "missing_skills": [],
        "extra_skills": [],
        "projects": [],
        "education": "",
        "experience": "",
        "score": 0
    }
    data =clean_json(result)
    data= safe_json_loads(result,fallback=fallback)
    for key,default in fallback.items():
        data.setdefault(key,default)
    if not data["projects"]:
        data["projects"] = extract_projects(user_text)
    return data
  except Exception as e:
      print("LLM解析失败：",e)
      return fallback