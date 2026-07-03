"""
统一日志模块
支持分级日志 + 文件滚动 + 控制台输出
"""

import logging
import sys
from pathlib import Path
from loguru import logger as _loguru_logger
from common.config import get_config

_LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"


def _setup_logger() -> None:
    """初始化日志配置"""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 移除 loguru 默认 handler
    _loguru_logger.remove()

    # 控制台输出（DEBUG 级别以上）
    _loguru_logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level="DEBUG",
        colorize=True,
    )

    # 文件输出（INFO 级别以上，按大小滚动）
    _loguru_logger.add(
        _LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )

    # 错误日志单独文件
    _loguru_logger.add(
        _LOG_DIR / "error_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="5 MB",
        retention="90 days",
        encoding="utf-8",
    )


# 全局 logger 实例
logger = _loguru_logger
_setup_logger()


def get_logger(name: str = None) -> logging.Logger:
    """
    获取标准 logging.Logger 适配器（兼容第三方库）
    :param name: 日志名称
    :return: logging.Logger 实例
    """
    std_logger = logging.getLogger(name or "study-coach")
    std_logger.setLevel(logging.DEBUG)
    # 转发到 loguru
    std_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    ))
    std_logger.addHandler(handler)
    return std_logger
