"""
家长消息推送模块
集成 Server酱，每日学习摘要推送
"""
import uuid
import requests
from datetime import datetime
from typing import Dict, List, Optional

from common.config import get_config
from common.database import execute_write
from common.logger import logger


def send_serverchan(title: str, content: str) -> bool:
    """
    通过 Server酱 推送消息
    :param title: 消息标题
    :param content: 消息内容（支持 Markdown）
    :return: 是否发送成功
    """
    token = get_config("parent_notify", "token", "")
    if not token:
        logger.warning("Server酱 Token 未配置，跳过推送")
        # 记录到数据库
        _log_notification(title, content, "pending")
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
            msg_id = result.get("data", {}).get("pushid", "")
            logger.info(f"Server酱推送成功: {title} (id={msg_id})")
            _log_notification(title, content, "sent")
            return True
        else:
            logger.error(f"Server酱推送失败: {result}")
            _log_notification(title, content, "failed")
            return False
    except Exception as e:
        logger.error(f"Server酱推送异常: {e}")
        _log_notification(title, content, "failed")
        return False


def _log_notification(title: str, content: str, status: str) -> None:
    """记录家长推送日志到数据库"""
    try:
        notify_id = f"notif_{uuid.uuid4().hex[:8]}"
        execute_write(
            """INSERT INTO parent_notifications
               (notify_id, title, content, send_status, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (notify_id, title, content, status, datetime.now().isoformat()),
        )
    except Exception as e:
        logger.warning(f"推送日志记录失败: {e}")


def send_daily_summary(stats: Dict) -> bool:
    """
    发送每日学习摘要
    :param stats: 学习统计数据
    :return: 是否发送成功
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


def send_goal_redeem_request(title: str, goal_title: str, reward_type: str, reward_desc: str) -> bool:
    """
    发送目标兑换请求通知
    :param goal_title: 目标名称
    :param reward_type: 奖励类型
    :param reward_desc: 奖励描述
    """
    content = (
        f"🎯 新兑换请求\n"
        f"目标: {goal_title}\n"
        f"奖励类型: {reward_type}\n"
        f"描述: {reward_desc}\n"
        f"请在系统中确认或驳回。"
    )
    return send_serverchan("🎁 兑换请求", content)


def send_parent_message(sender: str, message: str) -> bool:
    """
    发送家长留言通知
    """
    content = f"💬 来自{sender}的消息:\n\n{message}"
    return send_serverchan("📨 家长留言", content)
