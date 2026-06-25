

from app.config.skills_weight import WEIGHT
from app.config.skills_critical import CRITICAL_SKILLS
from app.utils.decorators import trace
import traceback
#经行职业匹配度评分,外加权重
@trace
def calculate_score(user_skills,job_skills,weights=None):
    # 修复：空 set 是 falsy，set([]) or [] 会退化为 list。
    # 正确做法是先把 None 转为空列表，再构建集合。
    user_set = set(user_skills or [])
    job_set = set(job_skills or [])
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
def critical_coverage(user_skills, critical_skills=None):
    # 防 None：先安全化为列表再构建集合，避免 set(None) → TypeError
    user_skills = user_skills or []
    if critical_skills is None:
        critical_skills = CRITICAL_SKILLS
    critical_skills = critical_skills or []

    if not critical_skills:
        return 100.0
    if not user_skills:
        return 0.0

    user_set = set(user_skills)
    critical_set = set(critical_skills)

    matched=user_set&critical_set
    score =len(matched)/len(critical_set)*100
    return round(score,2)
# 计算缺失技能惩罚分（0-100），缺失越多/技能越重要，惩罚越大
@trace
def calculate_missing(missing, job_skills, weights=None):
    missing = missing or []
    if not missing or not job_skills:
        return 0.0

    if weights is None:
        weights = WEIGHT

    job_set = set(job_skills)
    missing_set = set(missing)

    # 防御：只计算真正属于 JD 的缺失技能，防止外部传入脏数据导致分数溢出
    valid_missing = missing_set & job_set
    if not valid_missing:
        return 0.0

    # 按技能权重加权计算，重要技能缺失惩罚更大
    total_weight = sum(weights.get(s, 1) for s in job_set)
    missing_weight = sum(weights.get(s, 1) for s in valid_missing)

    # 加权缺失比例，钳制在 0-1 防止溢出
    ratio = min(1.0, missing_weight / max(1, total_weight))

    # 指数 1.5 让惩罚曲线在缺失较多时加速增长，缺失较少时保持温和
    score = (ratio ** 1.5) * 100

    return round(min(100.0, score), 2)




#技能的是否匹配的提示
@trace
def skills_report(user_skills, job_skills):
    # 防 None：set(None) 会抛 TypeError
    user_set = set(user_skills or [])
    job_set = set(job_skills or [])

    matched = sorted(list(user_set & job_set))
    missing = sorted(list(job_set - user_set))
    extra = sorted(list(user_set - job_set))
    return matched,missing,extra
# 计算最终适配度
@trace
def final_score(user_skills, job_skills, miss, weights=None, critical_skills=None):
    if weights is None:
        weights = WEIGHT

    # 1. 加权技能匹配分（0-100）
    skill_score = calculate_score(user_skills, job_skills, weights)

    # 2. 核心技能覆盖率（0-100）
    critical_score = critical_coverage(user_skills, critical_skills)

    # 3. 缺失技能惩罚（0-100），传入权重让重要技能缺失惩罚更大
    miss_score = calculate_missing(miss, job_skills, weights)

    # 4. 额外技能加分：候选人有但 JD 没要求的技能也是竞争力
    user_set = set(user_skills or [])
    job_set = set(job_skills or [])
    extra = user_set - job_set
    if extra and job_set:
        extra_weight = sum(weights.get(s, 1) for s in extra)
        job_total_weight = sum(weights.get(s, 1) for s in job_set)
        # 额外技能加分上限 100，取加权比 * 上限
        extra_score = min(100.0, (extra_weight / job_total_weight) * 100)
    else:
        extra_score = 0.0

    # 改进的加权公式：
    #   技能匹配 55% + 核心覆盖 25% + 额外技能奖励 10% - 缺失惩罚 10%
    #   四项组合更全面地反映真实匹配度，避免单一维度失真
    total = (
        skill_score * 0.55
        + critical_score * 0.25
        + extra_score * 0.10
        - miss_score * 0.10
    )

    # 钳制到 0-100，防止极端情况溢出
    total = max(0.0, min(100.0, total))
    return round(total, 2)