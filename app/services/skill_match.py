from app.config.skills_weight import WEIGHT
from app.config.skills_critical import CRITICAL_SKILLS
#经行职业匹配度评分,外加权重
def calculate_score(user_skills,job_skills,weights=None):
    user_set=set(user_skills)
    job_set=set(job_skills)
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
def critical_coverage(user_skills,critical_skills=None):
    if critical_skills in None:
        critical_skills=CRITICAL_SKILLS
    if not  critical_skills:
        return 100.0
    user_set=set(user_skills)
    critical_set=set(critical_skills)

    matched=user_set&critical_set
    score =len(matched)/len(critical_set)*100
    return round(score,2)

#技能的是否匹配的提示
def skills_report(user_skills,job_skills):
    user_set = set(user_skills)
    job_set = set(job_skills)

    matched = sorted(list(user_set & job_set))
    missing = sorted(list(job_set - user_set))
    extra = sorted(list(user_set - job_set))
    return matched,missing,extra
#计算最终适配度
def final_score(user_skills, job_skills, weights=None, critical_skills=None):
    skill_score=calculate_score(user_skills,job_skills,weights)
    critical_score = critical_coverage(user_skills, critical_skills)
    total=skill_score * 0.7+critical_score * 0.3
    return round(total,2)