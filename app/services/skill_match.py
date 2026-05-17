

from app.config.skills_weight import WEIGHT
from app.config.skills_critical import CRITICAL_SKILLS
from app.utils.tracer import trace
import traceback
#经行职业匹配度评分,外加权重
@trace
def calculate_score(user_skills,job_skills,weights=None):
    user_set=set(user_skills) or []
    job_set=set(job_skills) or []
    if not job_set:
        return 0.0
    if weights is None:
        weights = WEIGHT
    total_weight = 0
    matched_weight = 0
    for skill in job_skills:
        weight=weights.get(skill,1)
        total_weight +=weight
        if skill in user_set:
            matched_weight += weight
    if total_weight ==0:
        return 0.0
    score = matched_weight / total_weight*100
    return round(score,2)
#经行核心技能的覆盖率计算
@trace
def critical_coverage(user_skills,critical_skills=None):
    #经行防None处理
    user_skills=user_skills or []
    if critical_skills is None:
        critical_skills=CRITICAL_SKILLS
    critical_skills=critical_skills or []
    # 经行防None处理
    if not  critical_skills:
        return 100.0
    if not user_skills:
        return 0.0
    user_set=set(user_skills)
    critical_set=set(critical_skills)

    matched=user_set&critical_set
    score =len(matched)/len(critical_set)*100
    return round(score,2)
#目的是经行对于缺失技能减发
@trace
def calculate_missing(missing,job_skills):
    missing=missing or []
    if not missing:
        return 0.0
    missing_set=set(missing)
    job_skills_set=set(job_skills)
    score=len(missing_set)/len(job_skills_set)*100
    return round(score,2)




#技能的是否匹配的提示
@trace
def skills_report(user_skills,job_skills):
    user_set = set(user_skills)
    job_set = set(job_skills)

    matched = sorted(list(user_set & job_set))
    missing = sorted(list(job_set - user_set))
    extra = sorted(list(user_set - job_set))
    return matched,missing,extra
#计算最终适配度
@trace
def final_score(user_skills, job_skills,miss, weights=None, critical_skills=None):
    skill_score=calculate_score(user_skills,job_skills,weights)
    critical_score = critical_coverage(user_skills, critical_skills)
    miss_score=calculate_missing(miss,job_skills)
    total=skill_score * 0.7+critical_score * 0.2-miss_score *0.1
    return round(total,2)