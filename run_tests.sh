#!/bin/bash
# 测试运行脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  运行测试套件"
echo "============================================"

# 运行 pytest
python -m pytest tests/ \
    -v \
    --tb=short \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    "$@"

echo "============================================"
echo "  测试完成"
echo "============================================"
