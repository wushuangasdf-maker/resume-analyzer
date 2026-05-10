from  app.services.llm_service import chat
import json
#用于文本的整理，让ai更加精确的发挥
def llm_analyze(user_text,jd_text=None):
    prompt = f"""
        你是一个JSON生成器。
    必须严格返回合法JSON，不能包含任何解释、代码块或多余文本。
    格式如下：
        {{
        "skills": [],
        "missing_skills": [],
        "extra_skills": [],
        "projects": [],
        "education": "",
        "experience": "",
        "score": ""
        }}
        简历:
        {user_text}
    """
    if jd_text:
        prompt +=f"\n岗位描述:\n{jd_text}"
    result = chat(prompt)
    try:
        return json.loads(result)
    except:
        return {
            "skills": [],
            "projects": [],
            "jd_skills": [],
            "summary": result
        }