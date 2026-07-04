#!/bin/bash
# ============================================
# AI学习教练系统 - Linux 启动脚本
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=========================================="
echo "  AI学习教练系统 V1.0"
echo "=========================================="

# 1. 检查 Python 版本
echo ""
echo "[1/5] 检查 Python 版本..."
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PY_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    echo "❌ 需要 Python >= 3.10，当前版本: $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# 2. 安装依赖
echo ""
echo "[2/5] 检查依赖..."
MISSING=""
for pkg in flask pyyaml sqlalchemy requests schedule edge-tts pyttsx3 playwright opencv-python pillow numpy python-dotenv loguru openpyxl echarts-python; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        MISSING="$MISSING $pkg"
    fi
done

if [ -n "$MISSING" ]; then
    echo "安装缺失的依赖:$MISSING"
    pip install --break-system-packages $MISSING
    echo "✅ 依赖安装完成"
else
    echo "✅ 所有依赖已就绪"
fi

# 3. 初始化数据库
echo ""
echo "[3/5] 初始化数据库..."
mkdir -p data/logs data/uploads
python3 -c "
import sys; sys.path.insert(0, '.')
from common.database import init_db
init_db('db_schema.sql')
print('✅ 数据库初始化完成')
"

# 4. 检查 API 配置
echo ""
echo "[4/5] 检查配置..."
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，请创建并配置 DEEPSEEK_API_KEY"
    echo "   复制: cp .env.example .env"
else
    if grep -q "DEEPSEEK_API_KEY=" .env && grep "DEEPSEEK_API_KEY=" .env | grep -qv "^#"; then
        echo "✅ API 配置已就绪"
    else
        echo "⚠️  DEEPSEEK_API_KEY 未配置"
    fi
fi

# 5. 启动服务
echo ""
echo "[5/5] 启动服务..."
echo ""
echo "=========================================="
echo "  访问地址: http://localhost:5000"
echo "  日志文件: data/logs/app_$(date +%Y-%m-%d).log"
echo "  按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

python3 main.py
