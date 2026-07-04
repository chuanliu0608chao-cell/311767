"""
知识图谱模块测试
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.knowledge_graph import (
    add_knowledge_point,
    get_knowledge_graph,
    update_mastery,
    get_weak_points,
    link_error_to_knowledge,
)
from common.database import init_db


class TestKnowledgeGraph(unittest.TestCase):
    """知识图谱测试"""

    @classmethod
    def setUpClass(cls):
        init_db(os.path.join(os.path.dirname(__file__), "..", "db_schema.sql"))

    def test_add_knowledge_point(self):
        """测试添加知识点"""
        kp_id = add_knowledge_point(
            subject="math",
            name="函数求导",
            life_skill_tags=["逻辑思维"],
        )
        self.assertIsNotNone(kp_id)
        self.assertTrue(kp_id.startswith("kp_"))

    def test_get_knowledge_graph(self):
        """测试获取知识图谱"""
        result = get_knowledge_graph()
        self.assertIn("nodes", result)
        self.assertIn("edges", result)

    def test_update_mastery(self):
        """测试更新掌握程度"""
        kp_id = add_knowledge_point(subject="math", name="测试知识点")
        result = update_mastery(kp_id, 0.75)
        self.assertTrue(result)

    def test_get_weak_points(self):
        """测试获取薄弱知识点"""
        add_knowledge_point(subject="math", name="薄弱知识点", parent_kp_id=None)
        update_mastery(add_knowledge_point(subject="math", name="已掌握"), 0.9)
        weak = get_weak_points(threshold=0.6)
        self.assertIsInstance(weak, list)


if __name__ == "__main__":
    unittest.main()
