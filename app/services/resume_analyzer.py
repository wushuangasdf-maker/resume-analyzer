import json
from app.services.llm_service import chat
from app.utils.json_utils import clean_json,safe_json_loads
from app.utils.decorators import trace
from app.utils.ensure import ensure_str

# 将结构化简历数据发送给 AI，并返回稳定的 JSON 结果
@trace
def analyze_resume_structured(data):
    #1.默认返回的结构
    fallback={
        "score": 0,
        "strengths": [],
        "weaknesses": [],
        "recommended_positions": [],
        "skills_summary": {
            "matched_skills": [],
            "missing_skills": []
        },
        "suggestion": []
    }
    #判断是否是字典结构
    if not isinstance(data,dict):
        return fallback
    #经行prompt的构造
    prompt = f"""
    请基于以下结构化简历信息进行分析，并严格返回合法 JSON。
    结构如下：{{
      "score": 0,
      "strengths": [],
      "weaknesses": [],
      "recommended_positions": [],
      "skills_summary": {{
      "matched_skills": [],
      "missing_skills": []
  }},
      "suggestion":[]
    }}

要求：
   1. 只返回 JSON，不要添加解释或 Markdown。
   2. 所有字段必须存在。
   3. score 为 0-100 的数字。
   4. strengths：候选人的核心优势。
   5. weaknesses：待提升项。
   6. recommended_positions：推荐岗位。
   7. skills_summary:
      - matched_skills：已匹配技能
      - missing_skills：缺失技能
   8.suggestion：提升方向的建议
   返回格式:
   {json.dumps(fallback,ensure_ascii=False,indent=2)}
   结构话加你了数据:
   {json.dumps(data,ensure_ascii=False,indent=2)}
"""
    try:
        #4. 调用 LLM
        try:
          response = chat(prompt)
        except Exception as e:
            print(f"llm调用失败:{e}")
            fallback["weaknesses"] = ["AI分析失败"]
            return fallback

        if not response:
            return fallback
        # 5. JSON 安全解析
        response = ensure_str(response)
        result = safe_json_loads(response, fallback=fallback)

        if not isinstance(result, dict):
            return fallback
        # 限制在 0~100
        try:
          result["score"] = max(0, min(100, result["score"]))
        except Exception as e:
            return  "默认评级"

        return result

    except Exception as e:
        print("结构化简历分析失败:", e)
        return fallback

#综合引用
def analyze_resume_v2(text):
    # dict 直接传入，避免 str(dict) 产生 Python repr（单引号非 JSON）
    if isinstance(text, dict):
        return analyze_resume_structured(text)
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False) if isinstance(text, (dict, list)) else str(text)
    return analyze_resume_structured(text)