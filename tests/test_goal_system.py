"""
目标奖励系统测试
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.goal_system import (
    create_goal,
    get_goals,
    get_goal_by_id,
    earn_points,
    redeem_goal,
    confirm_redeem,
    cancel_redeem,
    get_points_balance,
)
from common.database import init_db


class TestGoalSystem(unittest.TestCase):
    """目标奖励系统测试"""

    @classmethod
    def setUpClass(cls):
        init_db(os.path.join(os.path.dirname(__file__), "..", "db_schema.sql"))

    def test_create_goal(self):
        """测试创建目标"""
        goal_id = create_goal(
            title="数学单元测试90分以上",
            target_points=50,
            description="下次数学测验达到90分以上",
        )
        self.assertIsNotNone(goal_id)
        self.assertTrue(goal_id.startswith("goal_"))

    def test_get_goals(self):
        """测试查询目标列表"""
        goals = get_goals()
        self.assertIsInstance(goals, list)

    def test_get_goal_by_id(self):
        """测试查询单个目标"""
        goal_id = create_goal(title="测试目标", target_points=10)
        goal = get_goal_by_id(goal_id)
        self.assertIsNotNone(goal)
        self.assertEqual(goal["title"], "测试目标")

    def test_earn_points(self):
        """测试获得积分"""
        point_id = earn_points("exam", "exam_001", points=20, description="完成试卷")
        self.assertIsNotNone(point_id)
        self.assertTrue(point_id.startswith("pt_"))

    def test_points_balance(self):
        """测试查询积分余额"""
        balance = get_points_balance()
        self.assertIn("total_points", balance)
        self.assertIn("available_points", balance)
        self.assertIn("frozen_points", balance)

    def test_redeem_goal_workflow(self):
        """测试目标兑换完整流程"""
        # 创建目标
        goal_id = create_goal(title="兑换测试", target_points=100)
        # 赚够积分
        earn_points("exam", "exam_test", points=100, description="测试积分")
        # 兑换
        result = redeem_goal(goal_id, "physical", "买一本数学练习册")
        self.assertEqual(result["status"], "frozen")

        # 确认兑换
        freeze_id = result["freeze_id"]
        confirm_result = confirm_redeem(freeze_id)
        self.assertEqual(confirm_result["status"], "deducted")

    def test_cancel_redeem(self):
        """测试取消兑换（驳回）"""
        goal_id = create_goal(title="取消测试", target_points=50)
        earn_points("exam", "exam_cancel", points=50)
        result = redeem_goal(goal_id, "experience", "看电影")
        freeze_id = result["freeze_id"]

        cancel_result = cancel_redeem(freeze_id)
        self.assertEqual(cancel_result["status"], "released")


if __name__ == "__main__":
    unittest.main()
