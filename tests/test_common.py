"""
公共模块测试
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.config import get_config, get_all
from common.database import init_db, execute_query


class TestConfig(unittest.TestCase):
    """配置模块测试"""

    def test_get_config_section(self):
        """测试获取配置节"""
        app_config = get_config("app")
        self.assertIsInstance(app_config, dict)
        self.assertIn("host", app_config)

    def test_get_config_key(self):
        """测试获取配置键"""
        port = get_config("app", "port")
        self.assertEqual(port, 5000)

    def test_get_all(self):
        """测试获取全部配置"""
        all_config = get_all()
        self.assertIsInstance(all_config, dict)
        self.assertIn("app", all_config)
        self.assertIn("database", all_config)
        self.assertIn("ai", all_config)


class TestDatabase(unittest.TestCase):
    """数据库模块测试"""

    @classmethod
    def setUpClass(cls):
        init_db(os.path.join(os.path.dirname(__file__), "..", "db_schema.sql"))

    def test_execute_query(self):
        """测试查询"""
        rows = execute_query("SELECT name FROM sqlite_master WHERE type='table'")
        self.assertGreater(len(rows), 0)

    def test_execute_write(self):
        """测试写操作"""
        import uuid
        uid = f"test_{uuid.uuid4().hex[:8]}"
        rows = execute_write(
            "INSERT INTO users (user_id, name) VALUES (99, ?)",
            (uid,),
        )
        self.assertGreater(rows, 0)


if __name__ == "__main__":
    unittest.main()
