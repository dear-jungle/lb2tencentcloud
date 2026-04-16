#!/bin/bash
# CLB 迁移工具启动脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

PORT=${PORT:-10041}
WORKERS=${WORKERS:-2}
DEV_MODE=${DEV_MODE:-1}

echo "============================================"
echo "  CLB 配置迁移工具"
echo "  阿里云 → 腾讯云"
echo "============================================"

# 解析参数
PROD_MODE=0
BUILD_FRONTEND=0
for arg in "$@"; do
    case $arg in
        --prod)   PROD_MODE=1; DEV_MODE=0 ;;
        --build)  BUILD_FRONTEND=1 ;;
    esac
done

# 前端构建（生产模式）
if [ "$BUILD_FRONTEND" = "1" ]; then
    echo "[构建] 前端打包..."
    cd frontend && npm install && npm run build && cd ..
    echo "[构建] 前端打包完成 → dist/"
fi

# 启动服务
if [ "$PROD_MODE" = "1" ]; then
    echo "[生产模式] 启动 Gunicorn（端口: $PORT, Workers: $WORKERS）"
    exec gunicorn server:app \
        --bind "0.0.0.0:$PORT" \
        --workers "$WORKERS" \
        --worker-class sync \
        --timeout 120 \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --log-level info
else
    echo "[开发模式] 启动 Gunicorn + 热重载（端口: $PORT）"
    mkdir -p logs
    exec gunicorn server:app \
        --bind "0.0.0.0:$PORT" \
        --workers 2 \
        --worker-class sync \
        --timeout 120 \
        --reload \
        --log-level debug
fi
