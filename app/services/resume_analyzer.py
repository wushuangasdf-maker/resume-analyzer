import json
import traceback

from click import prompt

from app.services.llm_service import chat
from app.utils.json_utils import clean_json,safe_json_loads

# 将结构化简历数据发送给 AI，并返回稳定的 JSON 结果
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
        }
    }
    #判断是否是字典结构
    if not isinstance(data,dict):
        return fallback
    #经行prompt的构造
    prompt = f"""
    请基于以下结构化简历信息进行分析，并严格返回合法 JSON。

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
   返回格式:
   {json.dumps(fallback,ensure_ascii=False,indent=2)}
   结构话加你了数据:
   {json.dumps(data,ensure_ascii=False,indent=2)}
"""
    try:
        #4. 调用 LLM
        response = chat(prompt)

        if not response:
            return fallback
        # 5. JSON 安全解析
        result = safe_json_loads(response, fallback=fallback)

        if not isinstance(result, dict):
            return fallback
        # 6. 补齐缺失字段
        result.setdefault("score", 0)
        result.setdefault("strengths", [])
        result.setdefault("weaknesses", [])
        result.setdefault("recommended_positions", [])
        result.setdefault(
            "skills_summary",
            {
                "matched_skills": [],
                "missing_skills": []
            }
        )
        # skills_summary 子字段补齐
        if not isinstance(result["skills_summary"], dict):
            result["skills_summary"] = {
                "matched_skills": [],
                "missing_skills": []
            }

        result["skills_summary"].setdefault("matched_skills", [])
        result["skills_summary"].setdefault("missing_skills", [])
        # 7. score 类型转换
        try:
            result["score"] = float(result["score"])
        except (ValueError, TypeError):
            result["score"] = 0

        # 限制在 0~100
        result["score"] = max(0, min(100, result["score"]))

        return result

    except Exception as e:
        print("结构化简历分析失败:", e)
        return fallback

#综合引用
def analyze_resume_v2(text):
    if not isinstance(text,str):
        text=str(text)
    result = analyze_resume_structured(text)
    return  result