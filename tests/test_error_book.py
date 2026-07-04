"""
错题本模块测试
"""
import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.error_book import (
    add_error_record,
    get_error_list,
    get_pending_reviews,
    get_today_stats,
    record_review,
)
from common.database import init_db


class TestErrorBook(unittest.TestCase):
    """错题本测试"""

    @classmethod
    def setUpClass(cls):
        """初始化测试数据库"""
        init_db(os.path.join(os.path.dirname(__file__), "..", "db_schema.sql"))

    def test_add_error_record(self):
        """测试添加错题"""
        record_id = add_error_record(
            question_id="q_test_001",
            subject="math",
            problem_text="已知 f(x) = x² + 2x，求 f'(x)",
            latex="f(x) = x^2 + 2x",
            knowledge_points=["函数求导", "幂函数"],
            wrong_answer="2x",
            correct_answer="2x + 2",
            difficulty="easy",
        )
        self.assertIsNotNone(record_id)
        self.assertTrue(record_id.startswith("err_"))

    def test_get_error_list(self):
        """测试查询错题列表"""
        result = get_error_list(page=1, page_size=20)
        self.assertIn("items", result)
        self.assertIn("total", result)
        self.assertIsInstance(result["items"], list)

    def test_get_today_stats(self):
        """测试今日统计"""
        stats = get_today_stats()
        self.assertIn("date", stats)
        self.assertIn("new_errors", stats)
        self.assertIn("pending_reviews", stats)

    def test_record_review_correct(self):
        """测试记录复习（答对）"""
        # 先添加一条错题
        record_id = add_error_record(
            question_id="q_test_002",
            subject="math",
            problem_text="2 + 2 = ?",
            difficulty="easy",
        )
        result = record_review(record_id, is_correct=True)
        self.assertIn("review_count", result)
        self.assertIn("is_mastered", result)

    def test_record_review_wrong(self):
        """测试记录复习（答错）"""
        record_id = add_error_record(
            question_id="q_test_003",
            subject="math",
            problem_text="3 × 4 = ?",
            difficulty="easy",
        )
        result = record_review(record_id, is_correct=False)
        self.assertEqual(result["review_count"], 1)


if __name__ == "__main__":
    unittest.main()
