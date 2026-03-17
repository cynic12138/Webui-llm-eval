# ===== Webui-LLM-Eval Windows 自动部署脚本 =====
# 用法: PowerShell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Info($msg)  { Write-Host "[INFO] $msg" -ForegroundColor Green }
function Warn($msg)  { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

# ---------- 1. 检查依赖 ----------
Info "检查系统依赖..."

function Check-Command($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Err "未找到 $name，请先安装。$hint"
    }
}

Check-Command "python" "推荐 Python 3.11: https://www.python.org/downloads/"
Check-Command "node" "推荐 Node.js 20+: https://nodejs.org/"
Check-Command "npm" ""
Check-Command "pm2" "安装: npm install -g pm2"

$PyVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Info "Python 版本: $PyVersion"
if ($PyVersion -notin @("3.10", "3.11", "3.12")) {
    Warn "推荐使用 Python 3.11（torch 兼容性最佳），当前为 $PyVersion"
}

$NodeVersion = (node -v) -replace 'v', '' -split '\.' | Select-Object -First 1
if ([int]$NodeVersion -lt 18) {
    Err "Node.js 版本过低，需要 18+"
}
Info "Node.js 版本: $(node -v)"

# ---------- 2. 环境变量文件 ----------
if (-not (Test-Path ".env")) {
    Info "未找到 .env，从 .env.example 复制..."
    Copy-Item ".env.example" ".env"
    Warn "请编辑 .env 文件配置数据库、Redis 等参数，然后重新运行此脚本"
    exit 0
}

Info "加载 .env 配置..."
$envVars = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $key = $Matches[1].Trim()
        $val = $Matches[2].Trim()
        $envVars[$key] = $val
        [Environment]::SetEnvironmentVariable($key, $val, "Process")
    }
}

$HOST_IP = if ($envVars.HOST_IP) { $envVars.HOST_IP } else { "localhost" }
$BACKEND_PORT = if ($envVars.BACKEND_PORT) { $envVars.BACKEND_PORT } else { "8000" }
$FRONTEND_PORT = if ($envVars.FRONTEND_PORT) { $envVars.FRONTEND_PORT } else { "3000" }
$DB_HOST = if ($envVars.DB_HOST) { $envVars.DB_HOST } else { "localhost" }
$DB_PORT = if ($envVars.DB_PORT) { $envVars.DB_PORT } else { "5432" }
$DB_USER = if ($envVars.DB_USER) { $envVars.DB_USER } else { "llmeval" }
$DB_PASS = if ($envVars.DB_PASS) { $envVars.DB_PASS } else { "llmeval123" }
$DB_NAME = if ($envVars.DB_NAME) { $envVars.DB_NAME } else { "llmeval" }

# ---------- 3. 安装 dotenv ----------
if (-not (Test-Path "package.json")) {
    Info "初始化根目录 package.json..."
    npm init -y --silent 2>$null | Out-Null
}
if (-not (Test-Path "node_modules/dotenv")) {
    Info "安装 dotenv..."
    npm install dotenv --save --silent 2>$null | Out-Null
}

# ---------- 4. 后端 Python 环境 ----------
Info "配置后端 Python 环境..."
Set-Location backend

if (-not (Test-Path ".venv")) {
    Info "创建 Python 虚拟环境..."
    python -m venv .venv
}

Info "安装 Python 依赖（可能需要几分钟）..."
& .venv\Scripts\pip install --upgrade pip -q
& .venv\Scripts\pip install -r requirements.txt -q

Set-Location $ScriptDir

# ---------- 5. 前端构建 ----------
Info "配置前端环境..."

# 生成 frontend/.env.local
Set-Content -Path "frontend\.env.local" -Value "NEXT_PUBLIC_API_URL=http://${HOST_IP}:${BACKEND_PORT}"
Info "已生成 frontend/.env.local: NEXT_PUBLIC_API_URL=http://${HOST_IP}:${BACKEND_PORT}"

Set-Location frontend

Info "安装前端依赖..."
npm ci --silent 2>$null
if ($LASTEXITCODE -ne 0) { npm install --silent }

Info "构建前端（可能需要几分钟）..."
npm run build

Set-Location $ScriptDir

# ---------- 6. 启动服务 ----------
Info "使用 PM2 启动所有服务..."
pm2 delete llmeval-backend llmeval-celery llmeval-frontend 2>$null
pm2 start ecosystem.config.js

# 等待后端启动
Info "等待后端启动..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:${BACKEND_PORT}/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
}

# ---------- 7. 完成 ----------
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  部署完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  前端地址: http://${HOST_IP}:${FRONTEND_PORT}" -ForegroundColor Green
Write-Host "  后端 API: http://${HOST_IP}:${BACKEND_PORT}" -ForegroundColor Green
Write-Host "  健康检查: http://${HOST_IP}:${BACKEND_PORT}/health" -ForegroundColor Green
Write-Host ""
Write-Host "  默认管理员账号: admin" -ForegroundColor Yellow
Write-Host "  默认管理员密码: admin123" -ForegroundColor Yellow
Write-Host ""
Write-Host "  PM2 管理命令:"
Write-Host "    pm2 status          # 查看服务状态"
Write-Host "    pm2 logs            # 查看日志"
Write-Host "    pm2 restart all     # 重启所有服务"
Write-Host "    pm2 stop all        # 停止所有服务"
Write-Host ""
