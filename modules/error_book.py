"""
错题本模块
实现错题自动分类入库、遗忘曲线复习提醒
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from common.database import execute_query, execute_write


def delete_error_record(record_id: str) -> bool:
    """删除错题记录及关联数据"""
    # 删除关联的复习记录
    execute_write(
        "DELETE FROM review_records WHERE record_id = ?",
        (record_id,),
    )
    # 删除错题与知识点的关联
    execute_write(
        "DELETE FROM error_knowledge_map WHERE record_id = ?",
        (record_id,),
    )
    # 删除错题记录本身
    execute_write(
        "DELETE FROM error_records WHERE record_id = ?",
        (record_id,),
    )
    return True


def get_error_detail(record_id: str) -> Optional[Dict]:
    """获取错题详细信息（含关联知识点）"""
    rows = execute_query(
        "SELECT * FROM error_records WHERE record_id = ?",
        (record_id,),
    )
    if not rows:
        return None

    record = rows[0]

    # 获取关联的知识点
    kp_rows = execute_query(
        """SELECT kp.name, kp.subject, kp.mastery_level
           FROM error_knowledge_map ek
           JOIN knowledge_points kp ON ek.kp_id = kp.kp_id
           WHERE ek.record_id = ?""",
        (record_id,),
    )
    record["knowledge_details"] = kp_rows if kp_rows else []

    # 获取关联的复习记录
    rev_rows = execute_query(
        "SELECT * FROM review_records WHERE record_id = ? ORDER BY review_date DESC",
        (record_id,),
    )
    record["reviews"] = rev_rows if rev_rows else []

    return record


# 间隔重复时间表（天）
REVIEW_INTERVALS = [1, 3, 7, 15]


def add_error_record(
    question_id: str,
    subject: str,
    problem_text: str,
    latex: str = "",
    knowledge_points: Optional[List[str]] = None,
    wrong_answer: str = "",
    correct_answer: str = "",
    difficulty: str = "medium",
    comment: str = "",
) -> str:
    """
    添加错题记录
    :param comment: 批改评语（可选）
    :return: record_id
    """
    record_id = f"err_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    execute_write(
        """INSERT INTO error_records
           (record_id, question_id, subject, problem_text, latex,
            knowledge_points, wrong_answer, correct_answer, difficulty, comment, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record_id, question_id, subject, problem_text, latex,
            ",".join(knowledge_points) if knowledge_points else "",
            wrong_answer, correct_answer, difficulty, comment, now,
        ),
    )

    # 初始化复习计划
    next_date = (datetime.now() + timedelta(days=REVIEW_INTERVALS[0])).isoformat()
    review_id = f"rev_{uuid.uuid4().hex[:8]}"
    execute_write(
        """INSERT INTO review_records
           (review_id, record_id, is_correct, review_date, next_review_date, status)
           VALUES (?, ?, 0, ?, ?, ?)""",
        (review_id, record_id, now, next_date, "pending"),
    )

    return record_id


def get_pending_reviews() -> List[Dict]:
    """获取今天需要复习的错题"""
    today = datetime.now().strftime("%Y-%m-%d")
    rows = execute_query(
        """SELECT er.*, rr.next_review_date, rr.review_count, rr.status as review_status
           FROM error_records er
           JOIN review_records rr ON er.record_id = rr.record_id
           WHERE rr.next_review_date <= ? AND rr.status != 'mastered'
           ORDER BY er.created_at DESC""",
        (today,),
    )
    return rows


def record_review(record_id: str, is_correct: bool) -> Dict:
    """
    记录一次复习结果
    :param record_id: 错题ID
    :param is_correct: 是否答对
    :return: 更新的复习计划
    """
    rows = execute_query(
        "SELECT * FROM review_records WHERE record_id = ? ORDER BY review_date DESC LIMIT 1",
        (record_id,),
    )
    if not rows:
        return {"error": "未找到复习记录"}

    current = rows[0]
    review_count = current.get("review_count", 0) + 1

    if is_correct:
        # 答对：升级到下一个间隔
        if review_count < len(REVIEW_INTERVALS):
            next_day = REVIEW_INTERVALS[review_count]
            status = "pending"
        else:
            next_day = 9999  # 无限远
            status = "mastered"
    else:
        # 答错：重置为第1天
        next_day = REVIEW_INTERVALS[0]
        status = "pending"

    next_date = (datetime.now() + timedelta(days=next_day)).isoformat()

    execute_write(
        """UPDATE review_records
           SET review_count = ?, next_review_date = ?, status = ?
           WHERE record_id = ? AND review_date = (
               SELECT MAX(review_date) FROM review_records WHERE record_id = ?)""",
        (review_count, next_date, status, record_id, record_id),
    )

    return {
        "review_count": review_count,
        "next_review_date": next_date,
        "status": status,
        "is_mastered": status == "mastered",
    }


def get_error_list(page: int = 1, page_size: int = 20, subject: str = None) -> Dict:
    """获取错题列表"""
    where = "WHERE 1=1"
    params = []
    if subject:
        where += " AND subject = ?"
        params.append(subject)

    offset = (page - 1) * page_size
    total_rows = execute_query(
        f"SELECT COUNT(*) as cnt FROM error_records {where}", tuple(params),
    )
    total = total_rows[0]["cnt"] if total_rows else 0

    rows = execute_query(
        f"""SELECT * FROM error_records {where}
            ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        (*params, page_size, offset),
    )

    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_today_stats() -> Dict:
    """获取今日学习统计"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 今日新增错题
    new_errors = execute_query(
        "SELECT COUNT(*) as cnt FROM error_records WHERE date(created_at) = ?",
        (today,),
    )
    new_count = new_errors[0]["cnt"] if new_errors else 0

    # 今日待复习
    pending = execute_query(
        """SELECT COUNT(*) as cnt FROM review_records
           WHERE next_review_date <= ? AND status != 'mastered'""",
        (today,),
    )
    pending_count = pending[0]["cnt"] if pending else 0

    return {
        "date": today,
        "new_errors": new_count,
        "pending_reviews": pending_count,
    }
