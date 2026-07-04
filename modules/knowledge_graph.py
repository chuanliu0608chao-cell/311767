"""
M17 知识图谱模块
知识点依赖关系构建
"""
from typing import Dict, List, Optional

from common.database import execute_query, execute_write
import uuid


def add_knowledge_point(
    subject: str,
    name: str,
    parent_kp_id: str = None,
    life_skill_tags: List[str] = None,
) -> str:
    """添加知识点"""
    kp_id = f"kp_{uuid.uuid4().hex[:8]}"
    tags = ",".join(life_skill_tags) if life_skill_tags else ""

    execute_write(
        """INSERT INTO knowledge_points
           (kp_id, subject, name, parent_kp_id, life_skill_tags)
           VALUES (?, ?, ?, ?, ?)""",
        (kp_id, subject, name, parent_kp_id or "", tags),
    )

    return kp_id


def get_knowledge_graph(subject: str = None) -> Dict:
    """
    获取知识图谱
    :return: {nodes: [...], edges: [...]}
    """
    where = ""
    params = ()
    if subject:
        where = "WHERE subject = ?"
        params = (subject,)

    nodes = execute_query(
        f"""SELECT kp_id, subject, name, mastery_level, life_skill_tags
            FROM knowledge_points {where}
            ORDER BY name""",
        params,
    )

    # 构建边（父子关系）
    edges = []
    for node in nodes:
        if node.get("parent_kp_id"):
            edges.append({
                "source": node["parent_kp_id"],
                "target": node["kp_id"],
                "relation": "prerequisite",
            })

    return {
        "nodes": nodes,
        "edges": edges,
    }


def update_mastery(kp_id: str, mastery_level: float) -> bool:
    """更新知识点掌握程度"""
    mastery_level = max(0.0, min(1.0, mastery_level))
    execute_write(
        "UPDATE knowledge_points SET mastery_level = ? WHERE kp_id = ?",
        (mastery_level, kp_id),
    )
    return True


def get_weak_points(subject: str = None, threshold: float = 0.6) -> List[Dict]:
    """获取薄弱知识点（掌握程度低于阈值）"""
    where = "WHERE mastery_level < ?"
    params = (threshold,)
    if subject:
        where += " AND subject = ?"
        params = (threshold, subject)

    rows = execute_query(
        f"SELECT * FROM knowledge_points {where} ORDER BY mastery_level ASC",
        params,
    )
    return rows


def link_error_to_knowledge(error_record_id: str, kp_ids: List[str]) -> None:
    """关联错题到知识点"""
    for kp_id in kp_ids:
        map_id = f"map_{uuid.uuid4().hex[:8]}"
        execute_write(
            "INSERT INTO error_knowledge_map (map_id, record_id, kp_id) VALUES (?, ?, ?)",
            (map_id, error_record_id, kp_id),
        )
