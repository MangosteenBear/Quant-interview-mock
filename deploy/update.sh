#!/bin/bash
# 日常更新脚本：git pull + 重启服务
# 用法：ssh ubuntu@124.221.191.102 "bash ~/Quant-interview-mock/deploy/update.sh"

set -e
cd ~/Quant-interview-mock

git pull origin main

# 如果 requirements.txt 有变动，重装依赖
cd backend
source .venv/bin/activate
pip install -r requirements.txt -q

sudo systemctl restart quantquiz
echo "[✓] 后端已重启"

# 前端构建（需要已安装 Node 18+）
if command -v npm &>/dev/null; then
    cd ../frontend
    npm install --silent
    npm run build:h5
    echo "[✓] 前端已构建"
else
    echo "[!] 未安装 Node，跳过前端构建"
fi

sudo systemctl status quantquiz --no-pager -l
