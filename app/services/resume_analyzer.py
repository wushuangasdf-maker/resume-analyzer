import json
import re
import logging
from app.services.llm_service import chat, chat_stream
from app.utils.json_utils import clean_json, safe_json_loads
from app.utils.decorators import trace
from app.utils.ensure import ensure_str

logger = logging.getLogger(__name__)

# 默认返回结构
FALLBACK = {
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


def _build_analysis_prompt(data: dict) -> str:
    """构建 JSON 分析 prompt — 供 API 非流式调用使用"""
    return f"""
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
   {json.dumps(FALLBACK, ensure_ascii=False, indent=2)}
   结构化简历数据:
   {json.dumps(data, ensure_ascii=False, indent=2)}
"""


# ---------------------------------------------------------------------------
# 流式输出专用 — Markdown 格式，便于逐字渲染
# ---------------------------------------------------------------------------

def _build_streaming_prompt(data: dict) -> str:
    """构建流式分析 prompt — 输出 Markdown，边分析边展示"""
    has_jd = bool(data.get("jd_skills"))
    score_line = f"当前技能匹配度评分为 {data.get('score', 'N/A')} 分（基于加权算法）。" if has_jd else ""

    return f"""
你是一位资深 HR 和职业规划顾问。请基于以下简历数据生成一份专业的简历分析报告。

{score_line}

要求：
1. 用 Markdown 格式输出，每个章节用 `##` 标题
2. 内容专业、具体，避免空洞的套话
3. 每个列表项独占一行，用数字编号（1. 2. 3.）
4. 严格按以下章节顺序输出，不要遗漏任何章节
5. 不要输出 JSON，直接输出可读的 Markdown 文本

输出格式：

## 🎯 综合评分
<分数>/100 - <一句话总结>

## 💪 核心优势
1. <具体优势一>
2. <具体优势二>
3. <具体优势三>

## 🔧 待提升项
1. <具体弱项一>
2. <具体弱项二>

## 🎯 推荐岗位
1. <岗位名称一> - <一句话理由>
2. <岗位名称二> - <一句话理由>
3. <岗位名称三> - <一句话理由>

## 💡 提升建议
1. <具体建议一>
2. <具体建议二>
3. <具体建议三>

## 🔑 技能摘要
已匹配技能：<逗号分隔>
缺失技能：<逗号分隔>

结构化简历数据:
{json.dumps(data, ensure_ascii=False, indent=2)}
"""


def _parse_streamed_markdown(text: str) -> dict:
    """将流式 Markdown 解析回结构化 dict，用于 Tab 展示"""
    result = {
        "score": 0,
        "strengths": [],
        "weaknesses": [],
        "recommended_positions": [],
        "skills_summary": {"matched_skills": [], "missing_skills": []},
        "suggestion": []
    }

    # ---- 提取评分 ----
    score_match = re.search(r'##\s*🎯\s*综合评[分]?\s*\n\s*(\d+)', text)
    if not score_match:
        score_match = re.search(r'(\d+)\s*/\s*100', text)
    if score_match:
        try:
            result["score"] = max(0, min(100, int(score_match.group(1))))
        except ValueError:
            pass

    # ---- 提取核心优势 ----
    strengths_section = _extract_section(text, ['💪 核心优势', '核心优势', '💪'])
    result["strengths"] = _parse_numbered_list(strengths_section)

    # ---- 提取待提升项 ----
    weaknesses_section = _extract_section(text, ['🔧 待提升项', '待提升项', '🔧'])
    result["weaknesses"] = _parse_numbered_list(weaknesses_section)

    # ---- 提取推荐岗位 ----
    positions_section = _extract_section(text, ['🎯 推荐岗位', '推荐岗位'])
    # 推荐岗位可能在第二个 🎯 出现，用更精确的匹配
    if not positions_section:
        # 尝试匹配第二次出现的 🎯
        parts = re.split(r'##\s*🎯', text)
        if len(parts) >= 3:
            positions_section = parts[2]  # 第三个 🎯 section (前两个是标题和评分)
    result["recommended_positions"] = _parse_numbered_list(positions_section)

    # ---- 提取提升建议 ----
    suggestion_section = _extract_section(text, ['💡 提升建议', '提升建议', '💡'])
    result["suggestion"] = _parse_numbered_list(suggestion_section)

    # ---- 提取技能摘要 ----
    skills_section = _extract_section(text, ['🔑 技能摘要', '技能摘要', '🔑'])
    if skills_section:
        matched_match = re.search(r'已匹配技能[：:]\s*(.+)', skills_section)
        if matched_match:
            result["skills_summary"]["matched_skills"] = [
                s.strip() for s in re.split(r'[，,、]', matched_match.group(1)) if s.strip()
            ]
        missing_match = re.search(r'缺失技能[：:]\s*(.+)', skills_section)
        if missing_match:
            result["skills_summary"]["missing_skills"] = [
                s.strip() for s in re.split(r'[，,、]', missing_match.group(1)) if s.strip()
            ]

    return result


def _extract_section(text: str, labels: list) -> str:
    """提取两个 ## 标题之间的内容"""
    for label in labels:
        # 匹配 ## emoji label 或 ## label
        pattern = rf'##\s*{re.escape(label)}\s*\n(.*?)(?=\n##\s|\Z)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return ""


def _parse_numbered_list(text: str) -> list:
    """解析数字编号列表: 1. xxx 2. xxx"""
    if not text:
        return []
    items = []
    for line in text.strip().split('\n'):
        line = line.strip()
        # 匹配 "1. xxx" 或 "1) xxx" 或 "- xxx"
        match = re.match(r'(?:\d+[.\)]\s*|[-•]\s*)(.+)', line)
        if match:
            item = match.group(1).strip()
            if item:
                items.append(item)
    return items if items else [text.strip()] if text.strip() else []


# ---------------------------------------------------------------------------
# API 调用入口
# ---------------------------------------------------------------------------

def _parse_analysis_response(response: str, fallback: dict) -> dict:
    """解析 LLM 返回的 JSON 结果"""
    if not response:
        return fallback
    response = ensure_str(response)
    result = safe_json_loads(response, fallback=fallback)
    if not isinstance(result, dict):
        return fallback
    try:
        result["score"] = max(0, min(100, result["score"]))
    except Exception:
        result["score"] = 0
    return result


@trace
def analyze_resume_structured(data):
    """将结构化简历数据发送给 AI，返回稳定的 JSON 结果（非流式，供 API 使用）"""
    if not isinstance(data, dict):
        return FALLBACK

    prompt = _build_analysis_prompt(data)

    try:
        response = chat(prompt)
    except Exception as e:
        logger.error("LLM 调用失败：%s", e)
        fallback = dict(FALLBACK)
        fallback["weaknesses"] = ["AI分析失败"]
        return fallback

    return _parse_analysis_response(response, dict(FALLBACK))


class StreamingAnalysis:
    """流式分析结果的可迭代包装器。

    每个实例独立持有 full_response，多线程/协程并发安全。

    用法:
        gen = analyze_resume_stream(intermediate)
        for token in gen:
            print(token, end="")
        result = _parse_streamed_markdown(gen.full_response)
    """

    def __init__(self, intermediate):
        self.full_response = ""
        # 解析输入
        if isinstance(intermediate, dict):
            self._data = intermediate
        elif isinstance(intermediate, str):
            try:
                self._data = json.loads(intermediate)
            except json.JSONDecodeError:
                self._data = {}
        else:
            self._data = {}

    def __iter__(self):
        return self._generate()

    def _generate(self):
        prompt = _build_streaming_prompt(self._data)
        try:
            for token in chat_stream(prompt):
                self.full_response += token
                yield token
        except Exception as e:
            logger.error("流式 LLM 调用失败：%s", e)
            yield "\n\n> ⚠️ AI 分析中断，请重试"


@trace
def analyze_resume_stream(intermediate):
    """流式分析 — 返回 StreamingAnalysis 实例，逐 token yield Markdown 报告。

    迭代完成后可通过 .full_response 获取完整文本，每个实例独立持有，线程安全。
    """
    return StreamingAnalysis(intermediate)


def analyze_resume_v2(text):
    """综合入口：dict 直接传入，字符串尝试解析"""
    if isinstance(text, dict):
        return analyze_resume_structured(text)
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False) if isinstance(text, (dict, list)) else str(text)
    return analyze_resume_structured(text)
