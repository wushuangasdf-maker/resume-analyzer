# ============================================================
# 技能关键词库 — 从 alias + weight + critical 自动推导，
# 避免手工维护导致的不一致。
# ============================================================
from app.config.skill_alias import skill_alias
from app.config.skills_weight import WEIGHT
from app.config.skills_critical import CRITICAL_SKILLS


def _build_skill_keywords():
    """汇集 alias values + weight keys + critical skills，全部小写去重"""
    pool = set()

    # alias 的标准名（values）
    for v in skill_alias.values():
        pool.add(v.lower().strip())

    # 权重表的 key
    for k in WEIGHT:
        pool.add(k.lower().strip())

    # 核心技能
    for s in CRITICAL_SKILLS:
        pool.add(s.lower().strip())

    # 补充一些 alias key 中本身就是标准名的（如 "python":"python"）
    for k in skill_alias:
        pool.add(k.lower().strip())

    return sorted(pool)


skill_keywords = _build_skill_keywords()


# 供 LLM prompt 使用的技能参考列表（人类可读格式）
SKILL_POOL_DISPLAY = ", ".join(skill_keywords)