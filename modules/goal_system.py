"""
目标奖励系统后端
实现目标 CRUD、积分联动、兑换状态机
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from common.database import execute_query, execute_write


def create_goal(title: str, target_points: int, description: str = "", deadline: str = None) -> str:
    """
    创建目标
    :return: goal_id
    """
    goal_id = f"goal_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    execute_write(
        """INSERT INTO goals
           (goal_id, title, description, target_points, current_points, status,
            progress_percent, created_at, deadline)
           VALUES (?, ?, ?, ?, 0, 'active', 0, ?, ?)""",
        (goal_id, title, description or "", target_points, now, deadline or ""),
    )

    return goal_id


def get_goals(status: str = None) -> List[Dict]:
    """获取目标列表"""
    where = ""
    params = ()
    if status:
        where = "WHERE status = ?"
        params = (status,)

    rows = execute_query(
        f"""SELECT *,
                   CASE WHEN target_points > 0 THEN ROUND(current_points * 100.0 / target_points, 1)
                        ELSE 0 END as progress_percent
            FROM goals {where}
            ORDER BY created_at DESC""",
        params,
    )
    return rows


def get_goal_by_id(goal_id: str) -> Optional[Dict]:
    """获取单个目标"""
    rows = execute_query("SELECT * FROM goals WHERE goal_id = ?", (goal_id,))
    return rows[0] if rows else None


def earn_points(source_type: str, source_id: str = None, points: int = 1, description: str = "") -> str:
    """
    获得积分
    :return: point_id
    """
    point_id = f"pt_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    execute_write(
        """INSERT INTO points_ledger
           (point_id, source_type, source_id, points, description, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (point_id, source_type, source_id or "", points, description or "", now),
    )

    # 更新目标进度
    _update_goal_progress(source_type, source_id, points)

    return point_id


def _update_goal_progress(source_type: str, source_id: str, points_earned: int) -> None:
    """更新目标进度"""
    # 查找关联的目标（通过 source_id）
    rows = execute_query(
        "SELECT goal_id, target_points, current_points FROM goals WHERE goal_id = ? AND status = 'active'",
        (source_id or "",),
    )
    for row in rows:
        new_total = (row.get("current_points") or 0) + points_earned
        execute_write(
            "UPDATE goals SET current_points = ?, progress_percent = ROUND(? * 100.0 / target_points, 1) WHERE goal_id = ?",
            (new_total, new_total, row["goal_id"]),
        )

        # 检查是否达成
        if new_total >= row["target_points"]:
            execute_write(
                "UPDATE goals SET status = 'confirmed', completed_at = ? WHERE goal_id = ?",
                (datetime.now().isoformat(), row["goal_id"]),
            )


def redeem_goal(goal_id: str, reward_type: str, reward_description: str = "") -> Dict:
    """
    兑换目标奖励
    状态机: active → frozen → confirmed → deducted
                  ↘ cancelled → released
    """
    goal = get_goal_by_id(goal_id)
    if not goal:
        return {"error": "目标不存在"}
    if goal["status"] != "confirmed":
        return {"error": f"目标状态不符合兑换条件: {goal['status']}"}

    # 冻结积分
    freeze_id = f"fz_{uuid.uuid4().hex[:8]}"
    execute_write(
        """INSERT INTO points_frozen
           (freeze_id, goal_id, freeze_points, freeze_reason, status)
           VALUES (?, ?, ?, ?, 'frozen')""",
        (freeze_id, goal_id, goal["current_points"], reward_description or "",),
    )

    # 更新目标状态
    execute_write(
        "UPDATE goals SET status = 'frozen' WHERE goal_id = ?",
        (goal_id,),
    )

    return {
        "freeze_id": freeze_id,
        "status": "frozen",
        "reward_type": reward_type,
        "message": "兑换申请已提交，等待家长确认",
    }


def confirm_redeem(freeze_id: str) -> Dict:
    """家长确认兑换 → 扣减积分"""
    rows = execute_query("SELECT * FROM points_frozen WHERE freeze_id = ?", (freeze_id,))
    if not rows:
        return {"error": "冻结记录不存在"}

    freeze = rows[0]
    execute_write(
        "UPDATE points_frozen SET status = 'deducted', released_at = ? WHERE freeze_id = ?",
        (datetime.now().isoformat(), freeze_id),
    )
    execute_write(
        "UPDATE goals SET status = 'cancelled' WHERE goal_id = ?",
        (freeze["goal_id"],),
    )

    return {"status": "deducted", "message": "兑换已确认，积分已扣除"}


def cancel_redeem(freeze_id: str) -> Dict:
    """家长驳回兑换 → 解冻积分"""
    rows = execute_query("SELECT * FROM points_frozen WHERE freeze_id = ?", (freeze_id,))
    if not rows:
        return {"error": "冻结记录不存在"}

    freeze = rows[0]
    execute_write(
        "UPDATE points_frozen SET status = 'released', released_at = ? WHERE freeze_id = ?",
        (datetime.now().isoformat(), freeze_id),
    )
    execute_write(
        "UPDATE goals SET status = 'active' WHERE goal_id = ?",
        (freeze["goal_id"],),
    )

    return {"status": "released", "message": "兑换已驳回，积分已恢复"}


def get_points_balance() -> Dict:
    """查询积分余额"""
    # 总积分
    rows = execute_query(
        "SELECT COALESCE(SUM(points), 0) as total FROM points_ledger"
    )
    total = rows[0]["total"] if rows else 0

    # 冻结积分
    rows = execute_query(
        "SELECT COALESCE(SUM(freeze_points), 0) as frozen FROM points_frozen WHERE status = 'frozen'"
    )
    frozen = rows[0]["frozen"] if rows else 0

    # 最近交易
    rows = execute_query(
        """SELECT * FROM points_ledger ORDER BY created_at DESC LIMIT 10"""
    )

    return {
        "total_points": total,
        "available_points": total - frozen,
        "frozen_points": frozen,
        "recent_transactions": rows,
    }
