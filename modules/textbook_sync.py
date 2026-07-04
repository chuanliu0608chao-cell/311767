"""
M7 课本同步模块
识别课本目录 → 匹配学习进度 → 生成拓展题
"""
import base64
import json
from typing import Dict, List, Optional

from common.api_client import ApiClient
from common.config import get_config
from common.logger import logger


class TextbookSyncEngine:
    """课本同步引擎"""

    def __init__(self, api_client: Optional[ApiClient] = None):
        self.client = api_client or ApiClient()
        ai_cfg = get_config("ai") or {}
        deepseek_cfg = ai_cfg.get("deepseek", {})
        self.config = {
            "base_url": deepseek_cfg.get("base_url", "https://api.deepseek.com/v1"),
            "model": deepseek_cfg.get("model", "deepseek-chat"),
            "api_key": deepseek_cfg.get("api_key", ""),
        }

    def identify_chapters(self, image_data: bytes, grade: str = "", subject: str = "math") -> Dict:
        """
        识别课本目录页，提取章节列表
        :param image_data: 课本目录页图片
        :param grade: 年级（可选，帮助更准确识别）
        :param subject: 学科
        :return: {textbook_name, grade, chapters: [{num, title, page}]}
        """
        b64_image = base64.b64encode(image_data).decode("utf-8")
        mime_type = "image/jpeg" if image_data[:4] == b'\xff\xd8\xff\xe0' else "image/png"

        grade_desc = f"（{grade}）" if grade else ""
        subject_names = {"math": "数学", "chinese": "语文", "english": "英语", "physics": "物理", "chemistry": "化学"}
        subject_name = subject_names.get(subject, subject)

        prompt = f"""你是一位教材编辑专家。请识别这张{subject_name}{grade_desc}课本的目录页。

请提取以下信息并按 JSON 格式输出：
{{
    "textbook_name": "课本名称（如：人教版初中数学八年级上册）",
    "grade": "年级",
    "subject": "{subject}",
    "chapters": [
        {{
            "chapter_num": 1,
            "title": "第一章 标题",
            "section_titles": ["第一节", "第二节"],
            "start_page": 1,
            "end_page": 20
        }}
    ],
    "total_chapters": 8
}}

要求：
1. 仔细识别所有章节标题和页码
2. 如果某章下有节（Section），也一并提取
3. 页码必须是数字
4. 只输出 JSON，不要其他内容"""

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_image}",
                            "detail": "high"
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        try:
            resp = self.client.post(
                f"{self.config['base_url']}/chat/completions",
                json_data={
                    "model": "deepseek-vl-3-0",  # 使用视觉模型
                    "messages": messages,
                    "max_tokens": 3000,
                    "temperature": 0.1,
                },
                headers={"Authorization": f"Bearer {self.config['api_key']}"},
            )
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")

            try:
                if "```" in content:
                    content = content.split("```")[1].replace("json", "").strip()
                result = json.loads(content)
                logger.info(f"课本目录识别成功: {result.get('textbook_name', '未知')}")
                return result
            except json.JSONDecodeError:
                logger.error(f"目录识别 JSON 解析失败: {content[:200]}")
                return {"error": "目录识别结果解析失败", "raw": content[:500]}

        except Exception as e:
            logger.error(f"课本目录识别失败: {e}")
            return {"error": str(e)}

    def match_progress(self, completed_chapters: List[str], textbook_chapters: List[Dict]) -> Dict:
        """
        匹配学习进度
        :param completed_chapters: 已完成的章节标题列表
        :param textbook_chapters: 课本所有章节
        :return: 进度分析
        """
        total = len(textbook_chapters)
        if total == 0:
            return {"error": "没有课本章节数据"}

        completed_set = set(completed_chapters)
        completed_count = 0
        completed_details = []
        remaining = []

        for ch in textbook_chapters:
            title = ch.get("title", "")
            if title in completed_set or str(ch.get("chapter_num", "")) in completed_set:
                completed_count += 1
                completed_details.append({
                    "chapter_num": ch.get("chapter_num"),
                    "title": title,
                    "status": "completed",
                })
            else:
                remaining.append({
                    "chapter_num": ch.get("chapter_num"),
                    "title": title,
                    "status": "pending",
                })

        progress = round(completed_count / total * 100, 1)

        return {
            "textbook_chapters": total,
            "completed": completed_count,
            "remaining": len(remaining),
            "progress_percent": progress,
            "completed_details": completed_details,
            "remaining_chapters": remaining,
        }

    def generate_extension_questions(
        self,
        subject: str,
        grade: str,
        chapters: List[str],
        count: int = 10,
    ) -> Dict:
        """
        根据学习进度生成拓展题
        :param subject: 学科
        :param grade: 年级
        :param chapters: 需要拓展的章节列表
        :param count: 题目数量
        :return: 拓展题列表
        """
        chapter_text = "、".join(chapters) if chapters else "综合"

        prompt = f"""你是一位{grade}{subject}教师。请为以下章节生成拓展练习题：

章节：{chapter_text}
题目数量：{count}
总分：100分

要求：
1. 题目难度略高于课本习题（巩固+拔高）
2. 覆盖所有指定章节的知识点
3. 每题标注知识点和分值
4. 提供标准答案和简要解析

按 JSON 格式输出：
{{
    "subject": "{subject}",
    "grade": "{grade}",
    "chapters": {chapters},
    "questions": [
        {{
            "id": 1,
            "type": "choice|fill_blank|calculation",
            "score": 10,
            "content": "题目内容",
            "latex": "LaTeX公式（如有）",
            "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"],
            "answer": "答案",
            "knowledge_point": "知识点",
            "difficulty": "medium|hard",
            "explanation": "解析"
        }}
    ]
}}"""

        messages = [
            {"role": "system", "content": f"你是一位专业的{subject}教师。"},
            {"role": "user", "content": prompt},
        ]

        try:
            resp = self.client.post(
                f"{self.config['base_url']}/chat/completions",
                json_data={
                    "model": self.config["model"],
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 4000,
                },
                headers={"Authorization": f"Bearer {self.config['api_key']}"},
            )
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")

            try:
                if "```" in content:
                    content = content.split("```")[1].replace("json", "").strip()
                result = json.loads(content)
                logger.info(f"拓展题生成成功: {len(result.get('questions', []))} 题")
                return result
            except json.JSONDecodeError:
                return {"error": "拓展题 JSON 解析失败", "raw": content[:500]}

        except Exception as e:
            logger.error(f"拓展题生成失败: {e}")
            return {"error": str(e)}


# 全局单例
_textbook_engine: Optional[TextbookSyncEngine] = None


def get_textbook_engine() -> TextbookSyncEngine:
    """获取课本同步引擎单例"""
    global _textbook_engine
    if _textbook_engine is None:
        _textbook_engine = TextbookSyncEngine()
    return _textbook_engine
