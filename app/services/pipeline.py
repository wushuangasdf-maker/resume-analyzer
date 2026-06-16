"""简历分析流水线 — api 和 web 模块共用。

将 LLM 抽取 → 兜底 → 归一化 → 评分 → 组装的完整流程封装为单一入口，
避免在多个界面模块中重复相同逻辑。
"""

import logging
from typing import Optional

from app.services.llm_analyze import llm_analyze
from app.services.skill_extractor import extract_keywords
from app.services.skill_normalizer import normalize_integrate_skill
from app.services.skill_match import final_score, skills_report

logger = logging.getLogger(__name__)


def run_analysis_pipeline(resume_text: str, jd_text: Optional[str] = None) -> dict:
    """执行完整分析流水线，返回中间结果。

    Args:
        resume_text: 简历纯文本
        jd_text: JD 纯文本，可选

    Returns:
        {
            "code": 200,
            "message": "success",
            "intermediate": {
                "skills": [...],
                "projects": [...],
                "jd_skills": [...],
                "score": <float|None>,
                "match": [...],
                "missing": [...],
                "extra": [...],
                "summary": "...",
            }
        }
    """
    # ---- 1. LLM 结构化抽取 -------------------------------------------------
    logger.info("开始 LLM 结构化抽取")
    data = llm_analyze(resume_text, jd_text)
    if not isinstance(data, dict):
        logger.warning("llm_analyze 返回异常类型，使用空字典兜底")
        data = {}

    # ---- 2. 兜底：LLM 没抽出技能时用本地规则提取 ---------------------------
    if not data.get("skills"):
        data["skills"] = extract_keywords(resume_text)
    if not data.get("jd_skills") and jd_text:
        data["jd_skills"] = extract_keywords(jd_text)

    # ---- 3. 技能归一化 -----------------------------------------------------
    skills = normalize_integrate_skill(data.get("skills") or [])
    jd_skills = normalize_integrate_skill(data.get("jd_skills") or [])

    # ---- 4. 技能匹配 & 评分 ------------------------------------------------
    if jd_skills:
        match, miss, extra = skills_report(skills, jd_skills)
        score = final_score(skills, jd_skills, miss)
    else:
        match, miss, extra = [], [], []
        score = None

    # ---- 5. 组装中间结果 ---------------------------------------------------
    intermediate = {
        "skills": skills,
        "projects": data.get("projects") or [],
        "jd_skills": jd_skills,
        "score": score,
        "match": match,
        "missing": miss,
        "extra": extra,
        "summary": data.get("summary", " ") or " ",
    }

    logger.info("流水线完成，抽取技能 %d 项，JD 技能 %d 项", len(skills), len(jd_skills))

    return {
        "code": 200,
        "message": "success",
        "intermediate": intermediate,
    }
