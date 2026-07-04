"""
预置示例数据脚本
在首次运行时检查并插入示例数据，方便演示和测试
"""
import uuid
import random
from datetime import datetime, timedelta
from common.database import execute_write, execute_query


def seed_demo_data():
    """预置示例错题、知识点和目标"""
    now = datetime.now()

    # 1. 预置知识点
    # 先插无父节点的，再插有父节点的
    demo_kps_no_parent = [
        ("math", "函数求导", 0.0),
        ("math", "三角函数", 0.0),
        ("math", "二次函数", 0.0),
        ("chinese", "文言文阅读", 0.0),
        ("chinese", "古诗词鉴赏", 0.0),
        ("english", "时态语态", 0.0),
        ("english", "阅读理解", 0.0),
        ("english", "语法填空", 0.0),
    ]
    demo_kps_with_parent = [
        ("math", "幂函数", "math:函数求导", 0.0),
        ("math", "复合函数求导", "math:幂函数", 0.0),
    ]

    # 先插无父节点的
    for subject, name, mastery in demo_kps_no_parent:
        existing = execute_query(
            "SELECT kp_id FROM knowledge_points WHERE subject = ? AND name = ?",
            (subject, name),
        )
        if not existing:
            kp_id = f"kp_{subject}_{name}"
            execute_write(
                """INSERT INTO knowledge_points (kp_id, subject, name, parent_kp_id, mastery_level)
                   VALUES (?, ?, ?, NULL, ?)""",
                (kp_id, subject, name, mastery),
            )

    # 再插有父节点的（FK 允许空字符串作为非引用值）
    for subject, name, parent_ref, mastery in demo_kps_with_parent:
        existing = execute_query(
            "SELECT kp_id FROM knowledge_points WHERE subject = ? AND name = ?",
            (subject, name),
        )
        if not existing:
            kp_id = f"kp_{subject}_{name}"
            # 通过 parent_ref 找到实际的 parent_kp_id
            parent_kp_id = ""
            if parent_ref:
                p_subject, p_name = parent_ref.split(":", 1)
                rows = execute_query(
                    "SELECT kp_id FROM knowledge_points WHERE subject = ? AND name = ?",
                    (p_subject, p_name),
                )
                if rows:
                    parent_kp_id = rows[0]["kp_id"]

            execute_write(
                """INSERT INTO knowledge_points (kp_id, subject, name, parent_kp_id, mastery_level)
                   VALUES (?, ?, ?, ?, ?)""",
                (kp_id, subject, name, parent_kp_id, mastery),
            )

    # 2. 预置错题
    demo_errors = [
        {
            "question_id": "demo_math_001",
            "subject": "math",
            "problem_text": "已知函数 f(x) = x³ + 2x² - x，求 f'(x)。",
            "latex": "f(x) = x^3 + 2x^2 - x",
            "knowledge_points": "函数求导,幂函数",
            "wrong_answer": "f'(x) = 3x²",
            "correct_answer": "f'(x) = 3x² + 4x - 1",
            "difficulty": "medium",
        },
        {
            "question_id": "demo_math_002",
            "subject": "math",
            "problem_text": "求函数 f(x) = sin(2x) 的导数。",
            "latex": "f(x) = \\sin(2x)",
            "knowledge_points": "三角函数,复合函数求导",
            "wrong_answer": "f'(x) = cos(2x)",
            "correct_answer": "f'(x) = 2cos(2x)",
            "difficulty": "medium",
        },
        {
            "question_id": "demo_english_001",
            "subject": "english",
            "problem_text": "She ___ (go) to school every day. 选择正确的动词形式。",
            "latex": "",
            "knowledge_points": "时态语态",
            "wrong_answer": "go",
            "correct_answer": "goes",
            "difficulty": "easy",
        },
        {
            "question_id": "demo_chinese_001",
            "subject": "chinese",
            "problem_text": "'学而时习之，不亦说乎'出自哪部经典？",
            "latex": "",
            "knowledge_points": "文言文阅读",
            "wrong_answer": "《孟子》",
            "correct_answer": "《论语》",
            "difficulty": "easy",
        },
        {
            "question_id": "demo_math_003",
            "subject": "math",
            "problem_text": "解方程：x² - 5x + 6 = 0",
            "latex": "x^2 - 5x + 6 = 0",
            "knowledge_points": "二次函数",
            "wrong_answer": "x = 1 或 x = 6",
            "correct_answer": "x = 2 或 x = 3",
            "difficulty": "easy",
        },
    ]

    for err in demo_errors:
        existing = execute_query(
            "SELECT record_id FROM error_records WHERE question_id = ?",
            (err["question_id"],),
        )
        if not existing:
            record_id = f"err_{uuid.uuid4().hex[:8]}"
            created = (now - timedelta(hours=random.randint(1, 48))).isoformat()
            execute_write(
                """INSERT INTO error_records
                   (record_id, question_id, subject, problem_text, latex,
                    knowledge_points, wrong_answer, correct_answer, difficulty, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record_id,
                    err["question_id"],
                    err["subject"],
                    err["problem_text"],
                    err["latex"],
                    err["knowledge_points"],
                    err["wrong_answer"],
                    err["correct_answer"],
                    err["difficulty"],
                    created,
                ),
            )

            # 初始化复习计划
            next_date = (now + timedelta(days=1)).isoformat()
            review_id = f"rev_{uuid.uuid4().hex[:8]}"
            execute_write(
                """INSERT INTO review_records
                   (review_id, record_id, review_date, next_review_date, status, is_correct)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (review_id, record_id, created, next_date, "pending", 0),
            )

    # 3. 预置目标
    demo_goals = [
        {
            "title": "数学单元测试 90 分以上",
            "target_points": 50,
            "description": "下次数学测验达到 90 分以上",
        },
        {
            "title": "一周掌握函数求导",
            "target_points": 30,
            "description": "完成函数求导相关 20 道练习题",
        },
    ]

    for goal in demo_goals:
        existing = execute_query(
            "SELECT goal_id FROM goals WHERE title = ?",
            (goal["title"],),
        )
        if not existing:
            goal_id = f"goal_{uuid.uuid4().hex[:8]}"
            now_iso = now.isoformat()
            execute_write(
                """INSERT INTO goals
                   (goal_id, title, description, target_points, current_points, status,
                    progress_percent, created_at)
                   VALUES (?, ?, ?, ?, 0, 'active', 0, ?)""",
                (goal_id, goal["title"], goal["description"], goal["target_points"], now_iso),
            )

    # 4. 预置积分记录
    demo_transactions = [
        {"source_type": "exam", "points": 20, "description": "完成数学测验"},
        {"source_type": "error_review", "points": 5, "description": "复习错题 1 道"},
        {"source_type": "daily_checkin", "points": 3, "description": "每日签到"},
    ]

    for tx in demo_transactions:
        existing = execute_query(
            "SELECT point_id FROM points_ledger WHERE source_type = ? AND description = ?",
            (tx["source_type"], tx["description"]),
        )
        if not existing:
            point_id = f"pt_{uuid.uuid4().hex[:8]}"
            created = (now - timedelta(hours=random.randint(1, 24))).isoformat()
            execute_write(
                """INSERT INTO points_ledger
                   (point_id, source_type, points, description, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (point_id, tx["source_type"], tx["points"], tx["description"], created),
            )

    print("✅ 示例数据预置完成")


if __name__ == "__main__":
    seed_demo_data()
