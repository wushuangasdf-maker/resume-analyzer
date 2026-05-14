import json
import traceback
from app.services.llm_service import chat
from app.utils.json_utils import clean_json,safe_json_loads

# 将结构化简历数据发送给 AI，并返回稳定的 JSON 结果
def analyze_resume_structured(data):
    prompt = f"""
请基于以下结构化简历信息进行分析：

{json.dumps(data, ensure_ascii=False)}

请严格返回以下 JSON 对象（不要添加任何解释）：

{{
  "score": 0,
  "strengths": [
    "优点1",
    "优点2"
  ],
  "weaknesses": [
    "缺点1",
    "缺点2"
  ],
  "recommended_positions": [
    "岗位1",
    "岗位2"
  ],
  "skills_summary": {{
    "matched_skills": [],
    "missing_skills": []
  }}
}}
"""

    response = chat(prompt)

    # 解析失败时的默认结构
    fallback = {
        "score": 0,
        "strengths": [],
        "weaknesses": [],
        "recommended_positions": [],
        "skills_summary": {
            "matched_skills": [],
            "missing_skills": []
        }
    }

    return safe_json_loads(response, fallback=fallback)
#综合引用
def analyze_resume_v2(text):
    if not isinstance(text,str):
        text=str(text)
    result = analyze_resume_structured(text)
    return  result