"""
家长消息推送模块
集成 Server酱，每日学习摘要推送
"""
import requests
from datetime import datetime
from typing import Dict, List, Optional

from common.config import get_config
from common.logger import logger


def send_serverchan(title: str, content: str) -> bool:
    """
    通过 Server酱 推送消息
    :param title: 消息标题
    :param content: 消息内容
    :return: 是否发送成功
    """
    token = get_config("parent_notify", "token", "")
    if not token:
        logger.warning("Server酱 Token 未配置，跳过推送")
        return False

    url = f"https://sctapi.ftqq.com/{token}.send"
    data = {
        "title": title,
        "desp": content,
    }

    try:
        resp = requests.post(url, data=data, timeout=10)
        result = resp.json()
        if result.get("code") == 0:
            logger.info(f"Server酱推送成功: {title}")
            return True
        else:
            logger.error(f"Server酱推送失败: {result}")
            return False
    except Exception as e:
        logger.error(f"Server酱推送异常: {e}")
        return False


def send_daily_summary(stats: Dict) -> bool:
    """
    发送每日学习摘要
    :param stats: 学习统计数据
    """
    title = f"📊 每日学习摘要 - {stats.get('date', datetime.now().strftime('%Y-%m-%d'))}"

    lines = [
        f"✅ 今日完成任务: {stats.get('completed_tasks', 0)}/{stats.get('total_tasks', 0)}",
        f"📝 今日新增错题: {stats.get('new_errors', 0)}",
        f"🔄 待复习错题: {stats.get('pending_reviews', 0)}",
        f"⭐ 今日获得积分: {stats.get('earned_points', 0)}",
    ]

    weak_points = stats.get("weak_points", [])
    if weak_points:
        lines.append(f"⚠️ 薄弱知识点: {', '.join(weak_points)}")

    suggestions = stats.get("tomorrow_suggestions", "")
    if suggestions:
        lines.append(f"💡 明日建议: {suggestions}")

    content = "\n\n".join(lines)
    return send_serverchan(title, content)
