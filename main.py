"""
主程序入口
支持两种模式：
  1. Flask API 服务模式（默认）
  2. --headless 模式（跳过看板，仅运行 API 服务）
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from common.config import get_config
from common.logger import logger


def parse_args():
    parser = argparse.ArgumentParser(description="AI学习教练系统 V1.0")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式：跳过看板，仅运行 API 服务"
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="启动 Flask API 服务（默认行为）"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("=" * 50)
    logger.info("  个人AI学习教练系统 V1.0")
    logger.info("=" * 50)

    if args.headless:
        logger.info("模式: 无头模式（仅 API 服务）")
    else:
        logger.info("模式: 完整模式（API 服务 + 看板）")

    if not args.serve:
        # 默认启动 Flask 服务
        from app import app, create_tables
        create_tables()
        host = get_config("app", "host", "0.0.0.0")
        port = get_config("app", "port", 5000)
        logger.info(f"🚀 启动 Flask 服务: http://{host}:{port}")
        app.run(host=host, port=port, debug=get_config("app", "debug", False))
    else:
        logger.info("✅ 已启动服务")


if __name__ == "__main__":
    main()
