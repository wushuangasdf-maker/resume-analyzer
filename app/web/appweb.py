
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
from app.services.resume_analyzer import analyze_resume_v2

# ---------------------------------------------------------------------------
# 页面配置
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI 简历分析器",
    page_icon="📄",
    layout="wide",
)

# ---------------------------------------------------------------------------
# 标题
# ---------------------------------------------------------------------------
st.title("📄 AI 简历分析器")
st.markdown("拖拽上传简历文件，AI 自动解析并生成深度分析报告。可选对比职位描述 (JD) 获取技能匹配度评分。")

# ---------------------------------------------------------------------------
# 侧边栏
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 分析选项")

    enable_jd = st.checkbox(
        "📋 启用 JD 对比",
        value=False,
        help="勾选后可上传职位描述文件，系统将对比简历与 JD 的技能匹配度",
    )

    st.divider()
    st.caption("📌 支持格式: PDF · DOCX · PNG · JPG")
    st.caption(f"📌 文件大小限制: {MAX_FILE_SIZE // 1024 // 1024} MB")

    if st.button("🔄 重置", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# 文件上传区域
# ---------------------------------------------------------------------------
if not enable_jd:
    # ===== 仅上传简历（不需要 JD） =====
    resume_file = st.file_uploader(
        "📤 拖拽或点击上传简历文件",
        type=["pdf", "docx", "png", "jpg", "jpeg"],
        help="必选 — 支持 PDF、DOCX 和图片格式",
        key="resume_uploader",
    )
    jd_file = None
else:
    # ===== 简历 + JD 双文件上传 =====
    col1, col2 = st.columns(2)
    with col1:
        resume_file = st.file_uploader(
            "📤 上传简历文件",
            type=["pdf", "docx", "png", "jpg", "jpeg"],
            help="必选 — 简历文件",
            key="resume_uploader_jd",
        )
    with col2:
        jd_file = st.file_uploader(
            "📋 上传 JD 文件（可选）",
            type=["pdf", "docx", "png", "jpg", "jpeg"],
            help="可选 — 职位描述文件，不上传则仅分析简历本身",
            key="jd_uploader",
        )

# ---------------------------------------------------------------------------
# 分析按钮
# ---------------------------------------------------------------------------
analyze_btn = st.button(
    "🔍 开始分析",
    type="primary",
    disabled=resume_file is None,
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def save_uploaded(uploaded_file) -> str:
    """安全保存上传文件，返回临时文件路径。"""
    # 大小校验
    data = uploaded_file.getvalue()
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)")

    # 安全文件名
    safe_name = _secure_filename(uploaded_file.name or "upload.tmp")
    _, ext = os.path.splitext(safe_name)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(data)
    tmp.close()
    return tmp.name


def run_pipeline(resume_file, jd_file=None) -> dict:
    """
    完整分析流水线（与 app/api/main.py 保持一致）。

    返回:
        {code, message, data: {filename, jd_filename, analysis}}
    """
    resume_path = None
    jd_path = None

    try:
        # ---- 1. 保存上传文件 ----
        resume_path = save_uploaded(resume_file)
        if jd_file:
            jd_path = save_uploaded(jd_file)

        # ---- 2. 解析文件文本 ----
        resume_text = parse_resume(resume_path)
        if not resume_text:
            return {"code": 400, "message": "简历内容为空或解析失败", "data": None}

        jd_text = parse_resume(jd_path) if jd_path else None

        # ---- 3. LLM 结构化抽取 ----
        data = llm_analyze(resume_text, jd_text)
        if not isinstance(data, dict):
            data = {}

        # ---- 4. 兜底技能提取 ----
        if not data.get("skills"):
            data["skills"] = extract_keywords(resume_text)
        if not data.get("jd_skills") and jd_text:
            data["jd_skills"] = extract_keywords(jd_text)

        # ---- 5. 技能归一化 ----
        skills = normalize_integrate_skill(data.get("skills") or [])
        jd_skills = normalize_integrate_skill(data.get("jd_skills") or [])

        # ---- 6. 技能匹配 & 评分 ----
        if jd_skills:
            match, miss, extra = skills_report(skills, jd_skills)
            score = final_score(skills, jd_skills, miss)
        else:
            match, miss, extra = [], [], []
            score = None

        # ---- 7. 组装中间结果 ----
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

        # ---- 8. 终局 AI 分析 ----
        result = analyze_resume_v2(intermediate)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "filename": resume_file.name,
                "jd_filename": jd_file.name if jd_file else None,
                "analysis": result,
            },
        }

    finally:
        # 清理临时文件
        for p in (resume_path, jd_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# 执行分析 & 展示结果
# ---------------------------------------------------------------------------
if analyze_btn and resume_file:
    with st.spinner("⏳ AI 正在分析您的简历，请稍候…"):
        try:
            response = run_pipeline(resume_file, jd_file)
        except Exception as exc:
            st.error(f"❌ 分析过程出现异常: {exc}")
            with st.expander("🔧 错误详情"):
                st.code(traceback.format_exc())
            st.stop()

    if not response or response.get("code") != 200:
        st.error(f"❌ 分析失败: {response.get('message', '未知错误') if response else '无响应'}")
        st.stop()

    # ===== 解析结果 =====
    analysis = response["data"]["analysis"]
    filename = response["data"]["filename"]
    jd_filename = response["data"].get("jd_filename")

    st.divider()

    # ===== 文件信息 =====
    if jd_filename:
        st.caption(f"📄 简历: {filename} ｜ 📋 JD: {jd_filename}")
    else:
        st.caption(f"📄 简历: {filename}")

    st.header("📊 分析报告")

    # ===== 综合评分 =====
    score = analysis.get("score")
    if score is not None:
        try:
            score_val = int(score)
        except (ValueError, TypeError):
            score_val = None

        if score_val is not None:
            # 分数颜色
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

            # 进度条
            st.progress(score_val / 100, text=f"综合匹配度 {score_val}%")
        else:
            # 非数字评分
            st.info(f"💬 综合评分: {score}")

    # ===== Tab 页展示详细结果 =====
    tab1, tab2, tab3, tab4 = st.tabs([
        "💪 核心优势",
        "🔧 待提升项",
        "🎯 推荐岗位",
        "💡 提升建议",
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

    # ===== 技能摘要 =====
    skills_summary = analysis.get("skills_summary") or {}
    if skills_summary:
        st.divider()
        st.subheader("🔑 技能摘要")

        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("**✅ 已匹配技能**")
            matched = skills_summary.get("matched_skills") or []
            if matched:
                for skill in matched:
                    st.markdown(f"- `{skill}`")
            else:
                st.caption("暂无")

        with sc2:
            st.markdown("**⚠️ 缺失技能**")
            missing = skills_summary.get("missing_skills") or []
            if missing:
                for skill in missing:
                    st.markdown(f"- `{skill}`")
            else:
                st.caption("暂无")

    # ===== 原始 JSON（折叠） =====
    with st.expander("📋 原始分析结果 (JSON)"):
        st.json(analysis)