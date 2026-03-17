#!/usr/bin/env bash
set -euo pipefail

# ===== Webui-LLM-Eval 自动部署脚本 =====
# 用法: chmod +x setup.sh && ./setup.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ---------- 1. 检查依赖 ----------
info "检查系统依赖..."

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        error "未找到 $1，请先安装。$2"
    fi
}

check_cmd python3 "推荐 Python 3.11: https://www.python.org/downloads/"
check_cmd node "推荐 Node.js 20+: https://nodejs.org/"
check_cmd npm ""
check_cmd pm2 "安装: npm install -g pm2"

# 检查 Python 版本
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Python 版本: $PY_VERSION"
if [[ "$PY_VERSION" != "3.11" && "$PY_VERSION" != "3.10" && "$PY_VERSION" != "3.12" ]]; then
    warn "推荐使用 Python 3.11（torch 兼容性最佳），当前为 $PY_VERSION"
fi

# 检查 Node 版本
NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if (( NODE_VERSION < 18 )); then
    error "Node.js 版本过低 ($(node -v))，需要 18+"
fi
info "Node.js 版本: $(node -v)"

# ---------- 2. 环境变量文件 ----------
if [ ! -f .env ]; then
    info "未找到 .env，从 .env.example 复制..."
    cp .env.example .env
    warn "请编辑 .env 文件配置数据库、Redis 等参数，然后重新运行此脚本"
    warn "  vi .env"
    exit 0
fi

info "加载 .env 配置..."
set -a
source .env
set +a

HOST_IP="${HOST_IP:-localhost}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-llmeval}"
DB_PASS="${DB_PASS:-llmeval123}"
DB_NAME="${DB_NAME:-llmeval}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# ---------- 3. 测试数据库和 Redis 连通性 ----------
info "测试 PostgreSQL 连通性 ($DB_HOST:$DB_PORT)..."
if command -v psql &>/dev/null; then
    if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" &>/dev/null; then
        info "PostgreSQL 连接成功"
    else
        warn "无法连接 PostgreSQL，请确认数据库已启动且凭据正确"
        warn "  创建数据库: CREATE USER $DB_USER WITH PASSWORD '$DB_PASS'; CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    fi
else
    warn "未安装 psql 客户端，跳过数据库连通性测试"
fi

info "测试 Redis 连通性 ($REDIS_HOST:$REDIS_PORT)..."
if command -v redis-cli &>/dev/null; then
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &>/dev/null; then
        info "Redis 连接成功"
    else
        warn "无法连接 Redis，请确认 Redis 已启动"
    fi
else
    warn "未安装 redis-cli，跳过 Redis 连通性测试"
fi

# ---------- 4. 安装 dotenv（ecosystem.config.js 依赖） ----------
if [ ! -f package.json ]; then
    info "初始化根目录 package.json..."
    npm init -y --silent >/dev/null 2>&1
fi

if [ ! -d node_modules/dotenv ]; then
    info "安装 dotenv..."
    npm install dotenv --save --silent >/dev/null 2>&1
fi

# ---------- 5. 后端 Python 环境 ----------
info "配置后端 Python 环境..."
cd backend

if [ ! -d .venv ]; then
    info "创建 Python 虚拟环境..."
    python3 -m venv .venv
fi

info "安装 Python 依赖（可能需要几分钟）..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

cd "$SCRIPT_DIR"

# ---------- 6. 前端构建 ----------
info "配置前端环境..."

# 自动生成 frontend/.env.local
cat > frontend/.env.local <<EOF
NEXT_PUBLIC_API_URL=http://${HOST_IP}:${BACKEND_PORT}
EOF
info "已生成 frontend/.env.local: NEXT_PUBLIC_API_URL=http://${HOST_IP}:${BACKEND_PORT}"

cd frontend

info "安装前端依赖..."
npm ci --silent 2>/dev/null || npm install --silent

info "构建前端（可能需要几分钟）..."
npm run build

cd "$SCRIPT_DIR"

# ---------- 7. 启动服务 ----------
info "使用 PM2 启动所有服务..."
pm2 delete llmeval-backend llmeval-celery llmeval-frontend 2>/dev/null || true
pm2 start ecosystem.config.js

# 等待后端启动
info "等待后端启动..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# ---------- 8. 完成 ----------
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  前端地址: ${GREEN}http://${HOST_IP}:${FRONTEND_PORT}${NC}"
echo -e "  后端 API: ${GREEN}http://${HOST_IP}:${BACKEND_PORT}${NC}"
echo -e "  健康检查: ${GREEN}http://${HOST_IP}:${BACKEND_PORT}/health${NC}"
echo ""
echo -e "  默认管理员账号: ${YELLOW}admin${NC}"
echo -e "  默认管理员密码: ${YELLOW}admin123${NC}"
echo ""
echo -e "  PM2 管理命令:"
echo "    pm2 status          # 查看服务状态"
echo "    pm2 logs            # 查看日志"
echo "    pm2 restart all     # 重启所有服务"
echo "    pm2 stop all        # 停止所有服务"
echo ""
