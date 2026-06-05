from app.services.llm_service import chat
import json
from app.services.project_extractor import extract_projects
from app.utils.json_utils import safe_json_loads, clean_json
from app.utils.decorators import trace
from app.utils.ensure import ensure_str

# 用于文本的整理，让 AI 更加精确地发挥
@trace
def llm_analyze(user_text, jd_text=None):
  fallback = {
      "skills": [],
      "jd_skills": [],
      "missing_skills": [],
      "extra_skills": [],
      "projects": [],
      "education": "",
      "experience": "",
      "score": 0,
      "suggestion": []
  }
  try:
    prompt = f"""
    你是一个专业的简历解析器。请仔细阅读以下简历，只提取简历中**实际出现**的信息。

    必须严格返回合法 JSON，不能包含任何解释、代码块或多余文本。
    格式：
    {{
      "skills": ["技能1", "技能2", ...],
      "jd_skills": [],
      "missing_skills": [],
      "extra_skills": [],
      "projects": ["项目经验1", "项目经验2", ...],
      "education": "教育背景摘要",
      "experience": "工作/实习经验摘要",
      "score": 0,
      "suggestion": []
    }}

    重要规则：
    1. skills 只提取简历中**明确提到**的技术技能（编程语言、框架、数据库、工具、云平台等）。
       绝不编造、猜测或列举简历中未出现的技能。
       技能名称使用通用标准名称（如 "React" 而非 "React.js"、"K8s" 统一为 "Kubernetes"）。
    2. projects 提取项目经历，每项一句话概括。
    3. education 和 experience 分别概括教育背景和工作经验。
    4. 若提供了 JD，才填写 jd_skills、missing_skills、extra_skills，否则留空数组。

    简历文本:
    {user_text}
    """
    if jd_text:
        prompt +=f"\n岗位描述:\n{jd_text}"
    try:
      result = chat(prompt)
    except Exception as e:
        print(f" llm调用失败：{e}")
        return fallback
    result = ensure_str(result)
    data = safe_json_loads(result, fallback=fallback)
    # 防护：LLM 可能返回数组而非对象
    if not isinstance(data, dict):
        data = fallback
    for key, default in fallback.items():
        data.setdefault(key, default)
    if not data["projects"]:
        data["projects"] = extract_projects(user_text)
    return data
  except Exception as e:
      print("LLM解析失败：",e)
      return fallback