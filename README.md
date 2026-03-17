# Webui-LLM-Eval — 企业级大语言模型评测平台

<p align="center">
  <strong>一站式 LLM 评测解决方案：多模型对比 · 标准基准测试 · 多维度评估 · 可视化报告</strong>
</p>

---

## 项目简介

Webui-LLM-Eval 是一个功能完整的大语言模型（LLM）评测 Web 平台，旨在为研究人员和工程团队提供标准化、可复现的模型评估能力。支持多模型并行评测、20+ 标准基准测试、LLM-as-Judge 智能评分、客观算法指标（ROUGE/BLEU/BERTScore 等）、实时进度推送、可视化结果分析和报告导出。

## 系统要求

| 组件 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Python | 3.10 | **3.11**（torch 兼容性最佳） |
| Node.js | 18 | **20+** |
| PostgreSQL | 14 | **15+** |
| Redis | 6 | **7+** |
| MinIO | 最新 | 最新 |
| PM2 | 5 | 最新 |

## 技术栈

| 层次 | 技术 |
|------|------|
| **前端** | Next.js 14 + TypeScript + Ant Design 5 + ECharts |
| **后端** | Python 3.11 + FastAPI + SQLAlchemy 2.0 + PostgreSQL 15 |
| **任务队列** | Celery + Redis 7 |
| **对象存储** | MinIO |
| **评测引擎** | 自研 Python 评测框架，支持 OpenAI/Anthropic/自定义 API |
| **部署** | Docker Compose / PM2 |

## 核心功能

### 评测能力
- **多模型并行评测** — 同一数据集在多个模型上同时评测，自动汇总对比
- **20+ 标准基准测试** — MMLU-Pro、GSM8K、HumanEval、C-Eval、HellaSwag、TruthfulQA、ARC、MATH、IFEval、LiveBench、BigCodeBench、HealthBench、MT-Bench、AlpacaEval、SWE-Bench
- **LLM-as-Judge** — 含位置偏差消除的双向评分机制
- **客观评估指标** — ROUGE-1/2/L、BLEU、METEOR、BERTScore、Exact Match、Token F1、Embedding 余弦相似度、Distinct-1/2、实体匹配 F1
- **幻觉检测** — 一致性采样法（N 次重复问答检测矛盾）
- **鲁棒性测试** — 同义词替换 / 拼写扰动 / 语序调整
- **代码执行验证** — Docker 沙箱 Pass@k 评测
- **安全/毒性检测** — 基于 Detoxify + 关键词规则
- **RAG 专项评测** — 忠实性 + 相关性评估
- **垂直领域评测** — 支持自定义领域标准的深度评测 + 诊断优化
- **一致性评测** — 多次采样一致性检验
- **指令遵循评测** — 格式约束遵循度评估
- **思维链评测** — CoT 推理质量评估
- **多轮对话评测** — 上下文保持能力测试
- **多语言评测** — 跨语言能力评估
- **结构化输出评测** — JSON/XML 等格式输出评估
- **工具调用评测** — Function Calling 能力测试

### 平台功能
- **API 性能分析** — TTFT / 延迟 / 吞吐量 / 成本估算
- **ELO 排名系统** — 基于历史对比的模型竞技排行
- **实时进度推送** — WebSocket + 轮询双保险，逐模型进度跟踪
- **可视化结果** — 雷达图 / 柱状图 / 分数分布 / 延迟对比
- **报告导出** — PDF / Excel / JSONL 一键导出
- **AI 助手** — 内置智能助手，支持评测结果解读
- **团队协作** — 多用户 / 团队管理 / 角色权限
- **通知中心** — 评测完成浏览器通知
- **Prompt 管理** — 提示词版本管理与实验对比

---

## 快速开始

> 以下三种部署方式任选其一。Docker Compose 最简单，推荐优先使用。

### 方式一：Docker Compose 部署（推荐，Windows / Linux / macOS 通用）

只需安装 Docker，无需手动安装 PostgreSQL、Redis、MinIO。

#### 前置条件

| 平台 | 安装 Docker |
|------|------------|
| **Windows** | 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，安装时勾选 WSL 2 后端。安装完成后启动 Docker Desktop 确保托盘图标显示 "Engine running" |
| **Linux (Ubuntu/Debian)** | `sudo apt update && sudo apt install -y docker.io docker-compose-plugin` 然后 `sudo usermod -aG docker $USER`（重新登录生效） |
| **macOS** | 安装 [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) |

#### 部署步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-username/Webui-llm-eval.git
cd Webui-llm-eval

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，按需修改密码和 HOST_IP（远程部署时改为服务器 IP）

# 3. 启动全部服务（首次会自动构建镜像，约 5-10 分钟）
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 访问
# 前端: http://localhost:3000
# API 文档: http://localhost:8000/docs
# MinIO 控制台: http://localhost:9001
```

常用管理命令：

```bash
docker-compose logs -f backend    # 查看后端日志
docker-compose restart backend    # 重启后端
docker-compose down               # 停止所有服务
docker-compose down -v            # 停止并删除数据卷（清空数据库）
```

---

### 方式二：Linux / macOS 原生部署

#### 前置条件安装

```bash
# === Ubuntu / Debian ===

# 1. Python 3.11
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 2. Node.js 20+
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 3. PM2
sudo npm install -g pm2

# 4. PostgreSQL 15
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql
# 创建数据库用户和库
sudo -u postgres psql -c "CREATE USER llmeval WITH PASSWORD 'llmeval123';"
sudo -u postgres psql -c "CREATE DATABASE llmeval OWNER llmeval;"

# 5. Redis 7
sudo apt install -y redis-server
sudo systemctl enable --now redis-server

# 6. MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/
# 启动 MinIO（后台运行）
MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin123 \
  nohup minio server /data/minio --console-address ":9001" &
```

#### 部署步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-username/Webui-llm-eval.git
cd Webui-llm-eval

# 2. 运行一键部署脚本
chmod +x setup.sh
./setup.sh
# 首次运行会生成 .env 文件，编辑后重新运行即可
```

部署脚本会自动：检查依赖 → 创建 Python 虚拟环境 → 安装依赖 → 构建前端 → PM2 启动所有服务。

---

### 方式三：Windows 原生部署

#### 前置条件安装

1. **Python 3.11** — 从 https://www.python.org/downloads/ 下载安装，安装时勾选 "Add Python to PATH"
2. **Node.js 20+** — 从 https://nodejs.org/ 下载 LTS 版本安装
3. **PM2** — 打开 PowerShell 执行：`npm install -g pm2`
4. **PostgreSQL 15** — 从 https://www.postgresql.org/download/windows/ 下载安装
   - 安装时记住设置的超级用户密码
   - 安装完成后打开 pgAdmin 或 SQL Shell (psql) 创建数据库：
   ```sql
   CREATE USER llmeval WITH PASSWORD 'llmeval123';
   CREATE DATABASE llmeval OWNER llmeval;
   ```
5. **Redis** — Windows 上推荐使用 [Memurai](https://www.memurai.com/) 或通过 WSL 安装：
   ```powershell
   # WSL 方式（推荐）
   wsl --install              # 如果还没有 WSL
   wsl sudo apt install -y redis-server
   wsl sudo service redis-server start
   ```
   或下载 [Redis for Windows](https://github.com/tporadowski/redis/releases) 解压后运行 `redis-server.exe`
6. **MinIO** — 从 https://dl.min.io/server/minio/release/windows-amd64/minio.exe 下载
   ```powershell
   # 启动 MinIO
   $env:MINIO_ROOT_USER="minioadmin"
   $env:MINIO_ROOT_PASSWORD="minioadmin123"
   .\minio.exe server D:\minio-data --console-address ":9001"
   ```

#### 部署步骤

```powershell
# 1. 克隆项目
git clone https://github.com/your-username/Webui-llm-eval.git
cd Webui-llm-eval

# 2. 运行部署脚本（PowerShell 管理员模式）
PowerShell -ExecutionPolicy Bypass -File setup.ps1
# 首次运行会生成 .env 文件，编辑后重新运行即可
```

> **Windows 注意事项**：
> - Celery 在 Windows 上使用 `--pool=solo` 模式运行（ecosystem.config.js 已自动处理）
> - 确保 PostgreSQL、Redis、MinIO 服务在运行 setup.ps1 之前已启动
> - 如果遇到 PowerShell 执行策略问题，以管理员身份运行 `Set-ExecutionPolicy RemoteSigned`

---

### 手动部署（高级）

如果不想使用部署脚本，可以手动执行以下步骤：

#### 1. 准备基础服务

确保 PostgreSQL、Redis、MinIO 已运行（安装方式参考上方对应平台的前置条件）。

#### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，修改 DB_HOST、DB_PASS、HOST_IP 等
```

#### 3. 安装后端

```bash
cd backend
python3.11 -m venv .venv           # Windows: python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

#### 4. 安装前端

```bash
cd frontend
npm ci
cp .env.local.example .env.local
# 编辑 .env.local 设置 NEXT_PUBLIC_API_URL（如 http://localhost:8000）
npm run build
cd ..
```

#### 5. 安装根目录依赖

```bash
npm install    # 安装 dotenv（ecosystem.config.js 需要）
```

#### 6. 启动服务

```bash
# PM2 启动（推荐）
pm2 start ecosystem.config.js

# 或手动启动各服务（需要多个终端窗口）：
# 后端:
cd backend && .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
# Windows: cd backend && .venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000

# Celery Worker:
cd backend && .venv/bin/celery -A app.core.celery_app worker --loglevel=info
# Windows: cd backend && .venv\Scripts\celery -A app.core.celery_app worker --loglevel=info --pool=solo

# 前端:
cd frontend && npx next start -p 3000
```

---

## 远程服务器部署示例

部署到 `10.10.0.102` 服务器只需修改 `.env` 中的几个值：

```bash
# .env
HOST_IP=10.10.0.102
DB_PASS=your_secure_password
SECRET_KEY=your_random_secret_key
```

运行 `./setup.sh`（Linux）或 `setup.ps1`（Windows）后：
- 后端 CORS 自动包含 `http://10.10.0.102:3000`
- `frontend/.env.local` 自动生成 `NEXT_PUBLIC_API_URL=http://10.10.0.102:8000`
- `ecosystem.config.js` 自动读取正确的数据库凭据和端口

---

## 环境变量说明

所有配置集中在根目录 `.env` 文件中：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HOST_IP` | 部署服务器 IP/域名 | `localhost` |
| `BACKEND_PORT` | 后端端口 | `8000` |
| `FRONTEND_PORT` | 前端端口 | `3000` |
| `DB_HOST` | PostgreSQL 地址 | `localhost` |
| `DB_PORT` | PostgreSQL 端口 | `5432` |
| `DB_USER` | PostgreSQL 用户名 | `llmeval` |
| `DB_PASS` | PostgreSQL 密码 | `llmeval123` |
| `DB_NAME` | 数据库名 | `llmeval` |
| `REDIS_HOST` | Redis 地址 | `localhost` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `MINIO_ENDPOINT` | MinIO 地址 | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO 用户名 | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO 密码 | `minioadmin123` |
| `SECRET_KEY` | JWT 签名密钥 | 需在生产环境修改 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间（分钟） | `1440` |
| `CORS_EXTRA_ORIGINS` | 额外 CORS 来源（逗号分隔） | 空 |
| `HTTP_PROXY` / `HTTPS_PROXY` | 代理设置 | 空 |

`frontend/.env.local` 由 `setup.sh` 自动从 `HOST_IP` + `BACKEND_PORT` 生成，无需手动维护。

---

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | 系统管理员 |

> 首次启动后端时自动创建，生产环境请及时修改密码。

---

## 使用流程

```
1. 注册/登录账户
   ↓
2. 添加模型配置（OpenAI / Anthropic / DashScope / DeepSeek / 自定义 OpenAI 兼容接口）
   ↓
3. 上传评测数据集（JSONL / JSON / CSV）或选择内置基准测试
   ↓
4. 创建评测任务（选择模型 + 数据集 + 评测维度）
   ↓
5. 实时查看评测进度（WebSocket 推送 + 逐模型进度）
   ↓
6. 查看多维度结果可视化（雷达图 / 柱状图 / 分数分布）
   ↓
7. 导出评测报告（PDF / Excel / JSONL）
   ↓
8. ELO 排行榜自动更新
```

## 数据集格式

### QA 问答评测 (JSONL)
```json
{"input": "什么是Transformer架构？", "output": "Transformer是一种基于自注意力机制的深度学习架构..."}
{"question": "请解释注意力机制", "answer": "注意力机制是一种让模型关注输入序列中不同位置的方法..."}
```

### 代码评测 (JSONL)
```json
{"prompt": "def add(a, b):\n    \"\"\"Add two numbers\"\"\"\n", "test": "assert add(1, 2) == 3", "entry_point": "add"}
```

### RAG 评测 (JSONL)
```json
{"input": "什么是检索增强生成？", "context": "RAG(Retrieval-Augmented Generation)是一种结合检索和生成的方法...", "output": "检索增强生成是..."}
```

### 多轮对话 (JSONL)
```json
{"messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好！"}, {"role": "user", "content": "介绍一下自己"}], "output": "我是一个AI助手..."}
```

## 模型配置说明

支持任何 OpenAI 兼容 API 接口，包括但不限于：

| 供应商 | 模型示例 | API 地址 |
|--------|----------|----------|
| OpenAI | gpt-4o, gpt-4o-mini | `https://api.openai.com/v1` |
| Anthropic | claude-sonnet-4-20250514 | `https://api.anthropic.com/v1` |
| 通义千问 | qwen3-max, qwen3-plus | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| DeepSeek | deepseek-chat, deepseek-reasoner | `https://api.deepseek.com/v1` |
| 智谱 | glm-4-plus | `https://open.bigmodel.cn/api/paas/v4` |
| vLLM 本地部署 | 任意模型 | `http://your-server:port/v1` |
| Ollama | llama3, qwen2 | `http://localhost:11434/v1` |

---

## 项目结构

```
Webui-llm-eval/
├── frontend/                    # Next.js 14 前端应用
│   ├── src/
│   │   ├── app/                 # App Router 页面
│   │   │   ├── (auth)/          # 认证相关页面（登录/注册）
│   │   │   └── (dashboard)/     # 主面板页面
│   │   ├── components/          # React 组件
│   │   ├── lib/                 # 工具函数、API 客户端、Hooks
│   │   └── types/               # TypeScript 类型定义
│   └── next.config.mjs
│
├── backend/                     # FastAPI 后端服务
│   ├── app/
│   │   ├── api/v1/              # REST API 路由
│   │   ├── core/                # 核心配置（安全、Celery、依赖注入）
│   │   ├── db/                  # 数据库模型和连接
│   │   ├── schemas/             # Pydantic 数据模型
│   │   └── services/            # 业务逻辑层
│   ├── main.py                  # 应用入口
│   └── requirements.txt
│
├── eval_engine/                 # 评测引擎核心
│   ├── engine.py                # 评测主引擎
│   ├── providers/               # LLM API 适配器
│   ├── evaluators/              # 各维度评测器
│   └── benchmark_data/          # 内置基准测试数据集
│
├── .env.example                 # 环境变量模板（统一配置源）
├── docker-compose.yml           # Docker Compose 编排
├── ecosystem.config.js          # PM2 进程管理配置（自动读取 .env）
├── setup.sh                     # Linux/macOS 一键部署脚本
├── setup.ps1                    # Windows 部署脚本
├── .python-version              # Python 版本声明（3.11）
└── README.md
```

---

## 开发指南

### 开发模式启动

```bash
# 启动基础设施（PostgreSQL + Redis + MinIO）
docker-compose up -d postgres redis minio

# 后端开发（热重载）
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Celery Worker（另一个终端）
cd backend
source .venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info --concurrency=2

# 前端开发（热重载）
cd frontend
npm run dev
```

### 添加新评测器

1. 在 `eval_engine/evaluators/` 下创建新的评测器文件
2. 实现评测逻辑，返回 0-1 归一化分数
3. 在 `eval_engine/engine.py` 的 `evaluate_sample()` 中集成
4. 在后端 Schema 中添加配置字段
5. 在前端评测创建页面添加对应选项

---

## 常见问题排查

### bcrypt 报错 / passlib 崩溃

```
AttributeError: module 'bcrypt' has no attribute '__about__'
```

原因：bcrypt 4.1+ 移除了 passlib 依赖的内部属性。已在 `requirements.txt` 中锁定 `bcrypt==4.0.1`。

```bash
cd backend
.venv/bin/pip install bcrypt==4.0.1
```

### 端口冲突

修改 `.env` 中的 `BACKEND_PORT` 和 `FRONTEND_PORT`，重新运行 `setup.sh` 即可。

### CORS 错误（跨域请求被拒绝）

1. 确认 `.env` 中 `HOST_IP` 设置正确（应为浏览器访问的地址）
2. 如需额外来源，设置 `CORS_EXTRA_ORIGINS=http://other-domain:port`
3. 重启后端：`pm2 restart llmeval-backend`

### 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
pg_isready -h localhost -p 5432

# 检查凭据是否匹配
PGPASSWORD=llmeval123 psql -h localhost -U llmeval -d llmeval -c "SELECT 1"

# 如果数据库不存在，手动创建
sudo -u postgres psql -c "CREATE USER llmeval WITH PASSWORD 'llmeval123';"
sudo -u postgres psql -c "CREATE DATABASE llmeval OWNER llmeval;"
```

### 前端无法连接后端

1. 检查 `frontend/.env.local` 中的 `NEXT_PUBLIC_API_URL` 是否指向正确的后端地址
2. 如果修改了地址，需要重新构建前端：`cd frontend && npm run build`
3. 重启前端：`pm2 restart llmeval-frontend`

### PM2 进程异常

```bash
pm2 logs llmeval-backend --lines 50   # 查看后端日志
pm2 logs llmeval-celery --lines 50    # 查看 Celery 日志
pm2 restart all                       # 重启所有服务
pm2 delete all && pm2 start ecosystem.config.js  # 完全重建
```

---

## 注意事项

- **生产环境**：请务必修改 `.env` 中的所有密码和 `SECRET_KEY`
- **数据库**：首次启动会自动创建表结构，无需手动执行迁移
- **基准数据**：内置 15+ 标准基准测试数据集，大型数据集（HealthBench 等）可通过 `eval_engine/benchmark_data/download_benchmarks.py` 按需下载
- **代码执行**：代码评测需要 Docker 环境支持沙箱执行
- **GPU 依赖**：安全检测（Detoxify）和 BERTScore 等功能使用 PyTorch，GPU 可加速但非必需
- **Windows 特别说明**：Celery 在 Windows 上以 `--pool=solo` 模式运行（单进程），性能低于 Linux 的多进程模式；生产环境建议使用 Linux 或 Docker

## License

MIT License
