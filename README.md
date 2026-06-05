AI 简历分析器 (AI Resume Analyzer)
简介：基于 LLM 的智能简历分析系统，支持多格式简历解析、JD（职位描述）对比、技能匹配度评分，并生成深度分析报告。

功能概览
1.多格式解析:支持 PDF、DOCX、PNG、JPG 格式的简历文件，自动提取文本（图片使用 OCR）
2.JD对比分析:可上传职位描述文件，对比简历与岗位要求的技能匹配度
3.智能技能抽取:LLM + 本地技能库双重提取，确保技能识别全面准确.
4.加权匹配评分：综合技能匹配度（55%）、核心覆盖率（25%）、额外技能奖励（10%）、缺失惩罚（10%）四维评分，避免出现某个权重过大或过小出现的分数失真情况
5.深度分析报告：AI生成结构化报告，包含综合评分、核心优势、待提升项、推荐岗位、提升建议，能够全面的发现简历和这个岗位要求的匹配度，进而经行简历的修改和自身能力的补充
6.双界面选择：FastAPI REST API（适合集成） + Streamlit Web UI（适合直接使用）
7.流式输出：Web 界面实时流式展示 AI 分析过程，可以更加直观的看出ai分析过程，进而减少等待生成过程中的枯燥感。
8.安全加固：文件类型校验、大小限制、路径遍历防护、CORS 白名单。
9.Docker 部署：非 root 用户运行，一键编排启动，体现项目可以快速部署的能力。

项目结构
```
resume-analyzer/
├── app/
│   ├── api/
│   │   ├── main.py              # FastAPI 应用入口（新版，完整流水线）
│   │   └── api.py               # 旧版 API 端点（兼容保留）
│   ├── config/
│   │   ├── skill_pool.py        # 技能关键词库
│   │   ├── skill_alias.py       # 技能别名映射
│   │   ├── skills_weight.py     # 技能权重配置
│   │   └── skills_critical.py   # 核心技能配置
│   ├── parsers/
│   │   ├── file_router.py       # 文件类型路由
│   │   ├── pdf_parser.py        # PDF 解析
│   │   ├── docx_parser.py       # DOCX 解析
│   │   ├── image_parser.py      # 图片 OCR 解析
│   │   └── text_clean.py        # 文本清洗
│   ├── services/
│   │   ├── llm_service.py       # LLM 调用（DeepSeek）
│   │   ├── llm_analyze.py       # LLM 结构化抽取
│   │   ├── llm_skill_extractor.py # AI 技能提取
│   │   ├── skill_extractor.py   # 技能提取整合
│   │   ├── skill_normalizer.py  # 技能归一化
│   │   ├── skill_match.py       # 技能匹配与评分
│   │   ├── project_extractor.py # 项目经验提取
│   │   └── resume_analyzer.py   # 终局 AI 分析（含流式）
│   ├── utils/
│   │   ├── json_utils.py        # JSON 安全解析
│   │   ├── decorators.py        # 工具装饰器
│   │   ├── ensure.py            # 类型安全工具
│   │   ├── logg.py              # 日志配置
│   │   └── skill_cache.py       # 技能处理缓存
│   ├── web/
│   │   └── appweb.py            # Streamlit Web 界面
│   └── main.py                  # 命令行入口
├── Dockerfile                   # Docker 镜像（安全加固）
├── docker-compose.yml           # 服务编排
├── requirements.txt             # Python 依赖
├── .env                         # 环境变量（API Key）
└── uploads/                     # 上传文件暂存目录
```

技术栈
类别 ：技术 
后端框架：FastAPI 0.115
前端界面：Streamlit 1.38
AI 模型：DeepSeek Chat API
文件解析：python-docx, PyPDF2, pdfplumber, Pillow, pytesseract
容器化：Docker + Docker Compose
运行环境：Python 3.11 

快速开始
1. 环境要求
Python 3.11+
Tesseract OCR（如需解析图片简历）
Docker & Docker Compose（可选，推荐）

2. 配置 API Key
```bash
# 编辑 .env 文件，填入你的 DeepSeek API Key
DEEPSEEK_API_KEY="sk-your-api-key-here"
```

3. 本地运行
```bash
# 创建虚拟环境
python -m venv .venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # Linux/macOS

# 安装依赖
pip install -r requirements.txt

# 启动 FastAPI 后端（端口 8000）
uvicorn app.api.main:app --reload --port 8000

# 启动 Streamlit 前端（端口 8501，新终端）
streamlit run app/web/appweb.py --server.port 8501
```

4. Docker 部署（推荐）
```bash
# 构建并启动全部服务
docker compose up -d --build

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

服务启动后：
- API 文档：http://localhost:8000/docs
- Web 界面：http://localhost:8501

## API 接口

### 健康检查

```
GET /ping
```

### 简历分析

```
POST /api/analyze
Content-Type: multipart/form-data
```

参数：
   参数  : 类型 : 必填 : 说明
  `file`: file : 必填 : 简历文件（PDF/DOCX/PNG/JPG）
`jd_file`:file : 选填 : JD 职位描述文件（可选）
**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "filename": "resume.pdf",
    "jd_filename": "jd.docx",
    "analysis": {
      "score": 85,
      "strengths": ["精通 Python 和机器学习框架", "5 年后端开发经验"],
      "weaknesses": ["缺乏云平台实战经验"],
      "recommended_positions": ["高级 Python 开发工程师", "AI 工程师"],
      "skills_summary": {
        "matched_skills": ["Python", "Django", "Docker"],
        "missing_skills": ["AWS", "Kubernetes"]
      },
      "suggestion": ["建议学习 AWS 认证课程", "参与开源云原生项目"]
    }
  }
}
```

## 分析流水线

```
简历文件 → 文件解析（PDF/DOCX/图片OCR）
          ↓
      LLM 结构化抽取（技能 / 项目 / 教育 / 经验）
          ↓
     技能归一化（别名映射 + AI 缓存）
          ↓
     匹配度评分（加权算法：技能 55% + 核心 25% + 额外 10% - 缺失 10%）
          ↓
     终局 AI 分析（评分 / 优劣势 / 推荐岗位 / 提升建议）
          ↓
      结构化报告
```

## 配置说明

| 配置项 | 位置 | 说明 |
|--------|------|------|
| API Key | `.env` | DeepSeek API Key |
| 技能权重 | `app/config/skills_weight.py` | 各技能在匹配中的权重 |
| 核心技能 | `app/config/skills_critical.py` | 需重点考核的核心技能列表 |
| 技能别名 | `app/config/skill_alias.py` | 技能名称归一化映射 |
| 最大文件大小 | `app/api/main.py` → `MAX_FILE_SIZE` | 默认 20MB |
| 允许文件类型 | `app/api/main.py` → `ALLOWED_EXTENSIONS` | PDF/DOCX/PNG/JPG |
| CORS 来源 | 环境变量 `CORS_ORIGINS` | 默认 `localhost:8501` |

## 安全特性
- 非 root 用户运行（Docker）
- 文件类型白名单校验
- 文件大小硬限制（默认 20MB）
- 文件名清洗防路径遍历
- CORS 来源白名单
- 上传文件即时清理
- `.env` 已加入 `.gitignore`，防止密钥泄露

## 命令行使用

```bash
# 直接运行命令行版本
python -m app.main

# 按提示输入简历路径，可选输入 JD 路径
# 输入简历文件所在位置：/path/to/resume.pdf
# 请输入JD文件(没有则回车)：/path/to/jd.docx
```

## License

MIT