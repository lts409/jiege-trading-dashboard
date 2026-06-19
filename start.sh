#!/bin/bash
# 杰哥交易仪表盘 — 启动脚本
# 用法: ./start.sh [port]

PORT=${1:-8899}
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 启动杰哥交易仪表盘..."
echo "   端口: $PORT"
echo "   配置: $DIR/config.json"

# 检查依赖
python3 -c "import flask" 2>/dev/null || {
  echo "📦 安装依赖..."
  pip3 install flask requests
}

# 启动
cd "$DIR"
python3 app.py &
echo "✅ 仪表盘已启动: http://127.0.0.1:$PORT"
echo "   停止: kill $(lsof -t -i :$PORT)"
