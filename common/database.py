"""
SQLite 数据库连接管理
单实例模式 + 重试机制 + 事务封装
"""

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common.config import get_config
from common.logger import logger

_DB_PATH: Optional[Path] = None
_CONNECTION_POOL: List[sqlite3.Connection] = []
_MAX_POOL_SIZE = 5


def _get_db_path() -> Path:
    """获取数据库文件路径"""
    global _DB_PATH
    if _DB_PATH is None:
        db_path_str = get_config("database", "path", "./data/study_coach.db")
        _DB_PATH = Path(db_path_str).resolve()
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return _DB_PATH


def _get_connection() -> sqlite3.Connection:
    """获取数据库连接（单实例模式，线程安全）"""
    # SQLite 单线程模式下直接用全局连接
    if not _CONNECTION_POOL:
        db_path = _get_db_path()
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # 启用 WAL 模式提升并发性能
        conn.execute("PRAGMA journal_mode=WAL")
        # 启用外键约束
        conn.execute("PRAGMA foreign_keys=ON")
        # 设置超时
        conn.execute(f"PRAGMA busy_timeout={get_config('database', 'retry_delay_ms', 5000)}")
        _CONNECTION_POOL.append(conn)
        logger.info(f"数据库连接已创建: {db_path}")
    return _CONNECTION_POOL[0]


def _close_connection(conn: sqlite3.Connection) -> None:
    """关闭数据库连接"""
    try:
        conn.close()
        if conn in _CONNECTION_POOL:
            _CONNECTION_POOL.remove(conn)
    except Exception as e:
        logger.warning(f"关闭数据库连接失败: {e}")


def init_db(schema_sql_path: Optional[str] = None) -> None:
    """
    初始化数据库表结构
    :param schema_sql_path: SQL 文件路径，默认使用项目内的 db_schema.sql
    """
    if schema_sql_path is None:
        schema_sql_path = str(Path(__file__).resolve().parent.parent / "db_schema.sql")

    conn = _get_connection()
    try:
        with open(schema_sql_path, "r", encoding="utf-8") as f:
            sql = f.read()
        conn.executescript(sql)
        logger.info(f"数据库表结构初始化完成: {schema_sql_path}")
    except FileNotFoundError:
        logger.warning(f"Schema 文件不存在，跳过初始化: {schema_sql_path}")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def execute_query(sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
    """
    执行查询语句，返回结果列表
    :param sql: SQL 查询语句
    :param params: 参数元组
    :return: 字典列表
    """
    retries = get_config("database", "retry_times", 3)
    last_error = None

    for attempt in range(retries):
        try:
            conn = _get_connection()
            cursor = conn.execute(sql, params)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return rows
        except sqlite3.OperationalError as e:
            last_error = e
            wait_time = 0.1 * (2 ** attempt)  # 指数退避
            logger.warning(f"查询执行失败 (尝试 {attempt + 1}/{retries}): {e}，{wait_time}s 后重试")
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"查询执行异常: {e}")
            raise

    raise RuntimeError(f"查询执行失败，已重试 {retries} 次: {last_error}")


def execute_write(sql: str, params: Tuple = ()) -> int:
    """
    执行写操作（INSERT/UPDATE/DELETE）
    :param sql: SQL 语句
    :param params: 参数元组
    :return: 影响的行数
    """
    retries = get_config("database", "retry_times", 3)
    last_error = None

    for attempt in range(retries):
        try:
            conn = _get_connection()
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid != -1 else cursor.rowcount
        except sqlite3.OperationalError as e:
            last_error = e
            conn.rollback()
            wait_time = 0.1 * (2 ** attempt)
            logger.warning(f"写操作失败 (尝试 {attempt + 1}/{retries}): {e}，{wait_time}s 后重试")
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"写操作异常: {e}")
            raise

    raise RuntimeError(f"写操作失败，已重试 {retries} 次: {last_error}")


def execute_transaction(statements: List[Tuple[str, Tuple]]) -> bool:
    """
    执行原子事务（多条语句要么都成功，要么都回滚）
    :param statements: [(sql, params), ...]
    :return: 是否成功
    """
    conn = _get_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        for sql, params in statements:
            conn.execute(sql, params)
        conn.commit()
        logger.info(f"事务执行成功，共 {len(statements)} 条语句")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"事务执行失败，已回滚: {e}")
        raise


def close_all() -> None:
    """关闭所有数据库连接"""
    for conn in _CONNECTION_POOL[:]:
        _close_connection(conn)
    logger.info("所有数据库连接已关闭")
