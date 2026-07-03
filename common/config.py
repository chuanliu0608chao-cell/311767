"""
公共配置加载器
从 config.yaml 加载配置，支持环境变量覆盖
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

_CONFIG_CACHE: Optional[Dict[str, Any]] = None
_CONFIG_PATH: Path = Path(__file__).resolve().parent.parent / "config.yaml"


def _load_config() -> Dict[str, Any]:
    """从 config.yaml 加载配置"""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件不存在: {_CONFIG_PATH}")

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # 解析环境变量占位符（如 "${DEEPSEEK_API_KEY}"）
    def _resolve_env(value: str) -> str:
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_key = value[2:-1]
            return os.environ.get(env_key, "")
        return value

    def _walk(obj):
        if isinstance(obj, dict):
            return {k: _walk(_resolve_env(v)) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(_resolve_env(item)) for item in obj]
        return _resolve_env(obj)

    _CONFIG_CACHE = _walk(raw)
    return _CONFIG_CACHE


def get_config(section: str = None, key: str = None, default: Any = None) -> Any:
    """
    获取配置值
    :param section: 配置顶层节名，如 "app", "database", "ai"
    :param key: 节内的键名
    :param default: 默认值
    :return: 配置值
    """
    cfg = _load_config()
    if section is None:
        return cfg
    if key is None:
        return cfg.get(section, {})

    section_data = cfg.get(section, {})
    if isinstance(section_data, dict):
        return section_data.get(key, default)
    return default


def get_all() -> Dict[str, Any]:
    """返回完整配置字典"""
    return _load_config()


def reload() -> None:
    """重新加载配置（用于热更新）"""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
    _load_config()
