"""
定时提醒模块
实现定时提醒、开机播报、触发式提醒
"""
import schedule
import time
from datetime import datetime
from typing import Callable, Dict, List

from common.config import get_config
from common.logger import logger

# 提醒调度器
_reminders: List[Dict] = []


def add_reminder(
    time_str: str,
    message: str,
    callback: Callable = None,
    repeat: bool = True,
) -> str:
    """
    添加定时提醒
    :param time_str: 时间字符串，如 "08:00"
    :param message: 提醒内容
    :param callback: 自定义回调函数
    :param repeat: 是否重复
    :return: reminder_id
    """
    reminder_id = f"rm_{len(_reminders) + 1}"
    _reminders.append({
        "id": reminder_id,
        "time": time_str,
        "message": message,
        "callback": callback,
        "repeat": repeat,
        "triggered": False,
    })

    # 注册 schedule 任务
    if callback:
        schedule.every().day.at(time_str).do(callback)
    else:
        schedule.every().day.at(time_str).do(_trigger_notification, reminder_id)

    logger.info(f"添加定时提醒: {time_str} - {message}")
    return reminder_id


def _trigger_notification(reminder_id: str):
    """触发通知"""
    reminder = None
    for r in _reminders:
        if r["id"] == reminder_id:
            reminder = r
            break

    if not reminder:
        return

    now_str = datetime.now().strftime("%H:%M")
    logger.info(f"🔔 提醒触发: [{now_str}] {reminder['message']}")

    # TODO: 调用 TTS 模块播放语音
    # TODO: 发送到 Windows 端弹窗展示


def get_boot_reminders() -> List[str]:
    """获取开机时要播报的今日目标"""
    today = datetime.now().strftime("%Y-%m-%d")
    return [
        f"今天是 {today}，今日待办提醒：{r['message']}"
        for r in _reminders
    ]


def start_scheduler():
    """启动定时提醒调度器"""
    logger.info("🔄 启动定时提醒调度器")

    # 开机播报
    boot_messages = get_boot_reminders()
    for msg in boot_messages:
        logger.info(f"📢 开机播报: {msg}")

    # 持续运行
    while True:
        schedule.run_pending()
        time.sleep(1)
