AI 简历分析器 (AI Resume Analyzer)
简介：基于 LLM 的智能简历分析系统，支持多格式简历解析、JD（职位描述）对比、技能匹配度评分，并生成深度分析报告。

功能概览
1. 多格式解析: 支持 PDF、DOCX、PNG、JPG 格式的简历文件，自动提取文本（图片使用 OCR）
2. JD 对比分析: 可上传职位描述文件，对比简历与岗位要求的技能匹配度
3. 智能技能抽取: LLM 结构化抽取 + 本地技能库兜底，确保技能识别全面准确
4. 技能归一化: 别名映射 + AI 缓存双重归一路径，将技能名称标准化
5. 加权匹配评分: 技能匹配度 + 核心覆盖率 + 额外技能奖励 - 缺失惩罚，多维评分避免失真
6. 深度分析报告: AI 生成 Markdown 结构化报告（含流式输出），覆盖综合评分、核心优势、待提升项、推荐岗位、提升建议、技能摘要六大板块
7. 共用分析流水线: pipeline 模块统一编排，API 与 Web 共享同一分析逻辑，避免代码重复
8. 双界面: FastAPI REST API（适合集成）+ Streamlit Web UI（流式渲染，适合直接使用）
9. 安全加固: 上传模块统一安全策略，文件类型校验、大小限制、路径遍历防护、CORS 白名单、非 root 容器运行
10. Docker 部署: 前后端分离编排，一键启动，非 root 用户运行

项目结构
```
resume-analyzer/
├── app/
│   ├── api/
│   │   └── main.py              # FastAPI 应用入口（v2.0.0，完整流水线）
│   ├── config/
│   │   ├── skill_pool.py        # 技能关键词库（自动从 alias+weight+critical 推导）
│   │   ├── skill_alias.py       # 技能别名映射
│   │   ├── skills_weight.py     # 技能权重配置
│   │   ├── skills_critical.py   # 核心技能配置
│   │   └── skill_cache.json     # AI 归一化结果持久化缓存
│   ├── parsers/
│   │   ├── file_router.py       # 文件类型路由
│   │   ├── pdf_parser.py        # PDF 解析
│   │   ├── docx_parser.py       # DOCX 解析
│   │   ├── image_parser.py      # 图片 OCR 解析
│   │   └── text_clean.py        # 文本清洗
│   ├── services/
│   │   ├── pipeline.py          # 分析流水线整合（API/Web 共用入口）
│   │   ├── llm_service.py       # LLM 调用（DeepSeek，含 chat + chat_stream）
│   │   ├── llm_analyze.py       # LLM 结构化抽取（技能/项目/教育/经验）
│   │   ├── llm_skill_extractor.py # AI 技能提取
│   │   ├── skill_extractor.py   # 技能提取整合（LLM + 本地规则兜底）
│   │   ├── skill_normalizer.py  # 技能归一化（别名 + AI 缓存）
│   │   ├── skill_match.py       # 技能匹配与加权评分
│   │   ├── project_extractor.py # 项目经验提取
│   │   └── resume_analyzer.py   # 终局 AI 分析（流式 Markdown + JSON 双模式）
│   ├── utils/
│   │   ├── upload.py            # 上传安全工具（扩展名校验/大小限制/文件名清洗）
│   │   ├── json_utils.py        # JSON 安全解析（嵌套括号提取、code block 清洗）
│   │   ├── pasers_utils.py      # 文本清洗与压缩（去噪/截断）
│   │   ├── skill_cache.py       # 技能缓存读写
│   │   ├── decorators.py        # 工具装饰器
│   │   ├── ensure.py            # 类型安全工具
│   │   └── logg.py              # 日志配置
│   ├── web/
│   │   └── appweb.py            # Streamlit Web 界面（流式渲染 + 技能可视化）
│   └── main.py                  # 命令行入口
├── Dockerfile                   # Docker 镜像（安全加固，非 root 运行）
├── docker-compose.yml           # 服务编排（api + web 分离部署）
├── requirements.txt             # Python 依赖
├── .env                         # 环境变量配置（需自行创建）
└── uploads/                     # 上传文件暂存目录
```

技术栈
| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.115 |
| 前端界面 | Streamlit 1.38 |
| AI 模型 | DeepSeek Chat API（兼容 OpenAI SDK） |
| 文件解析 | python-docx, PyPDF2, pdfplumber, Pillow, pytesseract |
| 容器化 | Docker + Docker Compose |
| 运行环境 | Python 3.11 |

快速开始
1. 环境要求
Python 3.11+
Tesseract OCR（如需解析图片简历）
Docker & Docker Compose（可选，推荐）

2. 配置 API Key
```bash
# 在项目根目录创建 .env 文件，填入你的 DeepSeek API Key
echo 'DEEPSEEK_API_KEY="sk-your-api-key-here"' > .env
# 或直接编辑 .env 文件
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

### 服务信息

```
GET /
```

### 简历分析

```
POST /analyze
Content-Type: multipart/form-data
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 必填 | 简历文件（PDF/DOCX/PNG/JPG） |
| `jd_file` | file | 选填 | JD 职位描述文件 |

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
         文本清洗（去噪、格式化）
              ↓
      LLM 结构化抽取（技能 / 项目 / 教育 / 经验 / 建议）
              ↓                    ↓
         抽取成功              抽取失败 → 本地规则兜底
              ↓
         技能归一化（别名映射 + AI 缓存合并）
              ↓
         匹配度评分（加权算法：技能匹配 + 核心覆盖 + 额外奖励 - 缺失惩罚）
              ↓
         终局 AI 分析（Markdown 流式 → 非流式 JSON 双模式输出）
              ↓
         结构化报告（6 大板块：评分 / 优势 / 弱项 / 推荐岗位 / 提升建议 / 技能摘要）
```

> **流式模式**: Web UI 使用 Markdown 流式输出，边生成边渲染，减少等待感。完成后自动解析为结构化 Tab 展示。

> **双模式输出**: 
> - API 端点 (`POST /analyze`) 直接返回结构化 JSON
> - Web 界面先展示流式 Markdown，再切换为交互式 Tab

> **共用流水线**: API 与 Web 复用同一 `run_analysis_pipeline()`，保证分析逻辑一致且安全策略统一。

## Web 界面功能

1. **文件上传**: 支持拖拽上传，简历 + 可选 JD 对比
2. **技能可视化**: 彩色标签展示全部提取技能，匹配（绿）/ 额外（橙）/ 缺失（红）一目了然
3. **分数卡片**: 大号渐变评分展示，根据分数高低自动变色
4. **结构化 Tab**: 核心优势 / 待提升项 / 推荐岗位 / 提升建议 四栏切换
5. **流式渲染**: AI 分析过程实时逐字展示
6. **原始报告**: 可展开查看完整 Markdown 原文

## 配置说明

| 配置项 | 位置 | 说明 |
|--------|------|------|
| API Key | `.env` | `DEEPSEEK_API_KEY` — DeepSeek API 密钥 |
| 技能权重 | `app/config/skills_weight.py` | 各技能在匹配中的权重 |
| 核心技能 | `app/config/skills_critical.py` | 需重点考核的核心技能列表 |
| 技能别名 | `app/config/skill_alias.py` | 技能名称归一化映射 |
| 技能库 | `app/config/skill_pool.py` | 自动从上述三项配置推导，无需手动维护 |
| 技能缓存 | `app/config/skill_cache.json` | AI 归一化结果持久化缓存（自动生成） |
| 最大文件大小 | `app/utils/upload.py` → `MAX_FILE_SIZE` | 默认 20MB |
| 允许文件类型 | `app/utils/upload.py` → `ALLOWED_EXTENSIONS` | PDF/DOCX/PNG/JPG |
| CORS 来源 | 环境变量 `CORS_ORIGINS` | 默认 `localhost:8501` |

## 安全特性
- 非 root 用户运行（Docker）
- 文件类型白名单校验（`app/utils/upload.py` 统一管理）
- 文件大小硬限制（默认 20MB，Content-Length + 流式双重校验）
- 文件名清洗防路径遍历（取 basename + 剥离特殊字符 + 随机前缀）
- CORS 来源白名单（不允许泛 `*`）
- 上传文件即时清理（finally 块保证）
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