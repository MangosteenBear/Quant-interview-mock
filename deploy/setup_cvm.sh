#!/bin/bash
# 腾讯 CVM 首次部署脚本
# 在服务器上以 ubuntu 用户执行：bash setup_cvm.sh
# 前提：已安装 PostgreSQL 16，DB 已迁移完毕

set -e

REPO="git@github.com:MangosteenBear/Quant-interview-mock.git"
APP_DIR="$HOME/Quant-interview-mock"

# ── 1. 系统依赖 ─────────────────────────────────────────────
sudo apt-get update -qq
sudo apt-get install -y python3.11 python3.11-venv python3-pip git

# ── 2. 拉取代码 ─────────────────────────────────────────────
if [ -d "$APP_DIR" ]; then
    echo "[*] 仓库已存在，跳过 clone"
else
    git clone "$REPO" "$APP_DIR"
fi

cd "$APP_DIR/backend"

# ── 3. Python 虚拟环境 ───────────────────────────────────────
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "[✓] Python 依赖安装完成"

# ── 4. .env 文件（首次部署手动填写） ─────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  请编辑 $APP_DIR/backend/.env，填入正确的 DATABASE_URL 后重新运行"
    echo "    nano $APP_DIR/backend/.env"
    exit 1
fi
echo "[✓] .env 文件已存在"

# ── 5. 安装 systemd 服务 ─────────────────────────────────────
sudo cp "$APP_DIR/deploy/quantquiz.service" /etc/systemd/system/quantquiz.service
sudo systemctl daemon-reload
sudo systemctl enable quantquiz
sudo systemctl restart quantquiz
echo "[✓] systemd 服务已启动"

sudo systemctl status quantquiz --no-pager
