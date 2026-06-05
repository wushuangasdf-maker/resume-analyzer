
import streamlit as st
import sys
import os
import re
import tempfile
import json
import traceback
import uuid

# ---------------------------------------------------------------------------
# 安全配置
# ---------------------------------------------------------------------------
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}


def _secure_filename(filename: str) -> str:
    """清洗文件名，防止路径遍历攻击。"""
    basename = os.path.basename(filename)
    basename = re.sub(r"[^\w一-鿿.\-() ]", "_", basename)
    if not basename or basename.startswith("."):
        basename = "upload.tmp"
    name, ext = os.path.splitext(basename)
    return f"{name}_{uuid.uuid4().hex[:8]}{ext}"

# ---------------------------------------------------------------------------
# 确保项目根在 Python 路径中（从 app/web/ 向上两级）
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.parsers.file_router import parse_resume
from app.services.llm_analyze import llm_analyze
from app.services.skill_extractor import extract_keywords
from app.services.skill_normalizer import normalize_integrate_skill
from app.services.skill_match import final_score, skills_report
from app.services.resume_analyzer import (
    analyze_resume_v2,
    analyze_resume_stream,
    _parse_streamed_markdown,
)
from app.utils.json_utils import safe_json_loads

# ---------------------------------------------------------------------------
# 页面配置
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI 简历分析器",
    page_icon="📄",
    layout="wide",
)

# ---- 自定义 CSS 微调 ----
st.markdown("""
<style>
    /* 按钮间距 */
    .stButton button { margin-top: 8px; }
    /* 评分卡片样式 */
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        color: white;
        margin: 16px 0;
    }
    .score-card .number {
        font-size: 4rem;
        font-weight: 800;
        line-height: 1;
    }
    .score-card .unit {
        font-size: 1.2rem;
        opacity: 0.7;
    }
    /* 流式输出区域 */
    .stream-box {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px 24px;
        border-left: 4px solid #667eea;
        min-height: 200px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 标题
# ---------------------------------------------------------------------------
st.title("AI 简历分析器")
st.caption("上传简历文件，AI 自动解析并生成深度分析报告。可选对比职位描述 (JD) 获取技能匹配度评分。")

# ---------------------------------------------------------------------------
# 侧边栏
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("分析选项")

    enable_jd = st.checkbox(
        "启用 JD 对比",
        value=False,
        help="勾选后可上传职位描述文件，系统将对比简历与 JD 的技能匹配度",
    )

    st.divider()
    st.caption("支持格式: PDF · DOCX · PNG · JPG")
    st.caption(f"文件大小限制: {MAX_FILE_SIZE // 1024 // 1024} MB")

    if st.button("重置", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# 文件上传区域 — 简历 key 统一，切换 JD 模式无需重新上传
# ---------------------------------------------------------------------------
if not enable_jd:
    resume_file = st.file_uploader(
        "拖拽或点击上传简历文件",
        type=["pdf", "docx", "png", "jpg", "jpeg"],
        help="必选 — 支持 PDF、DOCX 和图片格式",
        key="resume_uploader",
    )
    jd_file = None
else:
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        resume_file = st.file_uploader(
            "上传简历文件",
            type=["pdf", "docx", "png", "jpg", "jpeg"],
            help="必选 — 简历文件",
            key="resume_uploader",
        )
    with col2:
        jd_file = st.file_uploader(
            "上传 JD 文件（可选）",
            type=["pdf", "docx", "png", "jpg", "jpeg"],
            help="可选 — 职位描述文件",
            key="jd_uploader",
        )

# ---------------------------------------------------------------------------
# 分析按钮
# ---------------------------------------------------------------------------
analyze_btn = st.button(
    "开始分析",
    type="primary",
    disabled=resume_file is None,
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def save_uploaded(uploaded_file) -> str:
    """安全保存上传文件，返回临时文件路径。"""
    data = uploaded_file.getvalue()
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)")

    safe_name = _secure_filename(uploaded_file.name or "upload.tmp")
    _, ext = os.path.splitext(safe_name)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(data)
    tmp.close()
    return tmp.name


def run_pipeline(resume_file, jd_file=None) -> dict:
    """完整分析流水线。"""
    resume_path = None
    jd_path = None

    try:
        resume_path = save_uploaded(resume_file)
        if jd_file:
            jd_path = save_uploaded(jd_file)

        resume_text = parse_resume(resume_path)
        if not resume_text:
            return {"code": 400, "message": "简历内容为空或解析失败", "data": None}

        jd_text = parse_resume(jd_path) if jd_path else None

        data = llm_analyze(resume_text, jd_text)
        if not isinstance(data, dict):
            data = {}

        if not data.get("skills"):
            data["skills"] = extract_keywords(resume_text)
        if not data.get("jd_skills") and jd_text:
            data["jd_skills"] = extract_keywords(jd_text)

        skills = normalize_integrate_skill(data.get("skills") or [])
        jd_skills = normalize_integrate_skill(data.get("jd_skills") or [])

        if jd_skills:
            match, miss, extra = skills_report(skills, jd_skills)
            score = final_score(skills, jd_skills, miss)
        else:
            match, miss, extra = [], [], []
            score = None

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

        return {
            "code": 200,
            "message": "success",
            "data": {
                "filename": resume_file.name,
                "jd_filename": jd_file.name if jd_file else None,
                "intermediate": intermediate,
            },
        }

    finally:
        for p in (resume_path, jd_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


def display_structured_tabs(analysis):
    """用 Tab 展示解析后的结构化结果"""
    tab1, tab2, tab3, tab4 = st.tabs([
        "核心优势",
        "待提升项",
        "推荐岗位",
        "提升建议",
    ])

    with tab1:
        strengths = analysis.get("strengths") or []
        if strengths:
            for i, s in enumerate(strengths, 1):
                st.markdown(f"{i}. {s}")
        else:
            st.info("暂无数据")

    with tab2:
        weaknesses = analysis.get("weaknesses") or []
        if weaknesses:
            for i, w in enumerate(weaknesses, 1):
                st.markdown(f"{i}. {w}")
        else:
            st.info("暂无数据")

    with tab3:
        positions = analysis.get("recommended_positions") or []
        if positions:
            for i, p in enumerate(positions, 1):
                st.markdown(f"{i}. {p}")
        else:
            st.info("暂无数据")

    with tab4:
        suggestions = analysis.get("suggestion") or []
        if suggestions:
            for i, s in enumerate(suggestions, 1):
                st.markdown(f"{i}. {s}")
        else:
            st.info("暂无数据")


def display_skills_overview(intermediate):
    """展示简历中提取的全部技能，按匹配状态着色"""
    skills = intermediate.get("skills") or []
    if not skills:
        return

    match_set = set(intermediate.get("match") or [])
    missing_set = set(intermediate.get("missing") or [])
    extra_set = set(intermediate.get("extra") or [])
    has_jd = bool(intermediate.get("jd_skills"))

    st.divider()
    st.subheader("🔍 简历技能提取结果")
    st.caption(f"从简历中共提取 {len(skills)} 项技能" + ("（与 JD 对比）" if has_jd else ""))

    # 生成彩色标签
    badges = []
    for skill in sorted(skills):
        if has_jd:
            if skill in match_set:
                # 已匹配 — 绿色
                color = "#27ae60"
                bg = "#eafaf1"
                label = "✅ 匹配"
            elif skill in extra_set:
                # 简历有但 JD 不需要 — 橙色
                color = "#e67e22"
                bg = "#fef5e7"
                label = "📌 额外"
            else:
                # 默认蓝
                color = "#2980b9"
                bg = "#eaf2f8"
                label = ""
        else:
            # 无 JD 时统一蓝色
            color = "#2980b9"
            bg = "#eaf2f8"
            label = ""

        tooltip = label
        badge = (
            f'<span style="display:inline-block; background:{bg}; color:{color}; '
            f'padding:4px 12px; margin:3px; border-radius:20px; font-size:0.9rem; '
            f'border:1px solid {color}; white-space:nowrap;" '
            f'title="{tooltip}">{skill}</span>'
        )
        badges.append(badge)

    st.markdown(
        '<div style="line-height:2.2;">' + "".join(badges) + "</div>",
        unsafe_allow_html=True,
    )

    # 图例 + 缺失技能
    if has_jd:
        st.caption("")
        leg_cols = st.columns([1, 1, 1, 2])
        with leg_cols[0]:
            st.markdown(
                f'<span style="color:#27ae60; font-weight:bold;">●</span> '
                f'已匹配：{len(match_set)} 项</span>',
                unsafe_allow_html=True,
            )
        with leg_cols[1]:
            st.markdown(
                f'<span style="color:#e67e22; font-weight:bold;">●</span> '
                f'额外技能：{len(extra_set)} 项</span>',
                unsafe_allow_html=True,
            )
        with leg_cols[2]:
            st.markdown(
                f'<span style="color:#e74c3c; font-weight:bold;">●</span> '
                f'缺失：{len(missing_set)} 项</span>',
                unsafe_allow_html=True,
            )

        # 缺失技能列表（JD 要求但简历没有的）
        if missing_set:
            with st.expander("查看 JD 要求但简历缺失的技能"):
                missing_badges = [
                    f'<span style="display:inline-block; background:#fdedec; color:#e74c3c; '
                    f'padding:4px 12px; margin:3px; border-radius:20px; font-size:0.9rem; '
                    f'border:1px solid #e74c3c; white-space:nowrap;">{s}</span>'
                    for s in sorted(missing_set)
                ]
                st.markdown(
                    '<div style="line-height:2.2;">' + "".join(missing_badges) + "</div>",
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# 执行分析 & 流式展示结果
# ---------------------------------------------------------------------------
if analyze_btn and resume_file:
    # ===== 阶段 1：预处理 =====
    with st.status("正在分析简历...", expanded=True) as status:
        st.write("正在解析文件...")
        try:
            pipeline_result = run_pipeline(resume_file, jd_file)
        except Exception as exc:
            status.update(label="预处理失败", state="error")
            st.error(f"分析过程出现异常: {exc}")
            with st.expander("错误详情"):
                st.code(traceback.format_exc())
            st.stop()

        if not pipeline_result or pipeline_result.get("code") != 200:
            status.update(label="预处理失败", state="error")
            st.error(f"分析失败: {pipeline_result.get('message', '未知错误') if pipeline_result else '无响应'}")
            st.stop()

        intermediate = pipeline_result["data"]["intermediate"]
        filename = pipeline_result["data"]["filename"]
        jd_filename = pipeline_result["data"].get("jd_filename")

        st.write("AI 正在提取关键信息...")
        status.update(label="AI 正在生成分析报告...", state="running")

    # ===== 阶段 2：流式 AI 分析 =====
    st.divider()
    st.caption(f"简历: {filename}" + (f"  |  JD: {jd_filename}" if jd_filename else ""))

    # 使用 container 包裹流式输出区
    stream_container = st.container()
    with stream_container:
        stream_placeholder = st.empty()

    stream_gen = analyze_resume_stream(intermediate)
    full_response = ""

    for token in stream_gen:
        full_response += token
        # 用 Markdown 渲染，章节标题自然分行
        stream_placeholder.markdown(full_response + "▌")

    # 流式完成，去掉光标
    stream_placeholder.markdown(full_response)

    # 解析 Markdown → 结构化数据
    analysis = _parse_streamed_markdown(full_response)

    # ===== 阶段 3：结构化 Tab =====
    st.divider()
    st.subheader("分析报告摘要")

    # 分数卡片
    score = analysis.get("score")
    if score:
        try:
            score_val = int(score)
        except (ValueError, TypeError):
            score_val = 0

        if score_val >= 80:
            color = "#27ae60"
        elif score_val >= 60:
            color = "#f39c12"
        else:
            color = "#e74c3c"

        st.markdown(
            f"""
            <div style="text-align:center; margin:20px 0;">
                <span style="font-size:3.5rem; font-weight:bold; color:{color};">{score_val}</span>
                <span style="font-size:1.2rem; color:#888;"> / 100</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(score_val / 100, text=f"综合匹配度 {score_val}%")

    # ---- 技能提取总览（全部技能可视化）----
    display_skills_overview(intermediate)

    display_structured_tabs(analysis)

    # 原始文本折叠
    with st.expander("查看完整分析原文"):
        st.markdown(full_response)
