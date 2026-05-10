from app.parsers.file_router import parse_resume
from app.services.llm_analyze import llm_analyze
from app.services.skill_match import final_score, skills_report
from app.services.skill_normalizer import normalize_integrate_skill
from app.services.resume_analyzer import analyze_resume_v2
import json


def main():
    try:
        file_path = input("输入简历文件所在位置：")
        jd_input = input("请输入JD文件(没有则回车): ").strip()

        resume_text = parse_resume(file_path)
        if not resume_text:
            raise ValueError("简历为空")

        jd_text = parse_resume(jd_input) if jd_input else None

        # 1️⃣ 只调用一次 LLM（核心升级点）
        data = llm_analyze(resume_text, jd_text)

        # 2️⃣ 本地处理
        skills = normalize_integrate_skill(data["skills"])
        jd_skills = normalize_integrate_skill(data.get("jd_skills", []))

        # 3️⃣ 评分
        score = final_score(skills, jd_skills) if jd_skills else None
        match, miss, extra = skills_report(skills, jd_skills) if jd_skills else ([], [], [])

        # 4️⃣ 输出结果
        result = {
            "skills": skills,
            "projects": data["projects"],
            "jd_skills": jd_skills,
            "score": score,
            "match": match,
            "missing": miss,
            "extra": extra,
            "summary": data.get("summary", "")
        }
        result = analyze_resume_v2(result)
        print("\n================ 优化后分析结果 ================\n")
        print(json.dumps(result, ensure_ascii=False, indent=4))

    except Exception as e:
        print("出现错误：", str(e))


if __name__ == "__main__":
    main()