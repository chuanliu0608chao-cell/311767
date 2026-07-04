"""
M4 拍题识别模块
封装 Claude Vision API 调用，支持图片识别、LaTeX 公式提取、知识点标注
"""
import base64
import json
from typing import Dict, List, Optional

from common.config import get_config
from common.logger import logger
from common.api_client import ApiClient


class PhotoRecognitionEngine:
    """照片识别引擎（Claude Vision）"""

    def __init__(self, api_client: Optional[ApiClient] = None):
        self.client = api_client or ApiClient()
        ai_cfg = get_config("ai") or {}
        claude_cfg = ai_cfg.get("claude", {})
        self.config = {
            "base_url": claude_cfg.get("base_url", "http://127.0.0.1:15721"),
            "model": claude_cfg.get("model", "claude-sonnet-4-6"),
            "max_tokens": claude_cfg.get("max_tokens", 3000),
            "temperature": claude_cfg.get("temperature", 0.3),
        }

    def recognize_photo(
        self,
        image_data: bytes,
        subject: str = "math",
        description: str = "",
    ) -> Dict:
        """
        识别照片中的题目
        :param image_data: 图片二进制数据
        :param subject: 学科
        :param description: 额外描述
        :return: 识别结果
        """
        # 编码为 base64
        b64_image = base64.b64encode(image_data).decode("utf-8")
        mime_type = "image/jpeg" if image_data[:4] == b'\xff\xd8\xff\xe0' else "image/png"

        prompt = f"""你是一位经验丰富的教师。请识别这张照片中的题目内容。

学科：{subject}
{f"额外说明：{description}" if description else ""}

请完成以下任务：

【题目识别】
1. 识别题目文字内容
2. 如果是数学题，提供 LaTeX 格式的公式
3. 提取涉及的知识点
4. 判断难度（easy/medium/hard）
5. 如果是选择题，列出4个选项
6. 如果是计算题，给出标准答案和解题步骤

【批改痕迹识别】
7. 识别学生手写的答案（黑色/蓝色笔迹）
8. 识别老师的批改标记：
   - ✓ 或 + 表示正确
   - ✗ 或 × 表示错误
   - 红线划掉的部分表示错误
   - 圈出的数字表示扣分
9. 判断每道题是否正确（correct: true/false）
10. 如果有批改评语，提取评语内容

请按以下 JSON 格式输出（不要输出其他内容）：
{{
    "questions": [
        {{
            "question_num": 1,
            "recognized_text": "题目文字",
            "latex": "LaTeX公式（如有）",
            "knowledge_points": ["知识点1", "知识点2"],
            "difficulty": "medium",
            "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"],
            "standard_answer": "标准答案",
            "solution_steps": ["步骤1", "步骤2"],
            "student_answer": "学生填写的答案",
            "teacher_marks": ["✓", "✗", "红线标注"],
            "is_correct": true,
            "comment": "批改评语（如有）"
        }}
    ],
    "summary": {{
        "total_questions": 9,
        "correct_count": 7,
        "wrong_count": 2,
        "wrong_questions": [6, 7],
        "score_estimate": "85/100"
    }}
}}"""

        logger.info(f"Claude Vision 识别照片: subject={subject}")

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
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ]

        try:
            resp = self.client.post(
                f"{self.config['base_url']}/chat/completions",
                json_data={
                    "model": self.config["model"],
                    "messages": messages,
                    "max_tokens": self.config["max_tokens"],
                    "temperature": self.config["temperature"],
                },
            )

            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")

            # 尝试解析 JSON
            try:
                if "```" in content:
                    content = content.split("```")[1].replace("json", "").strip()
                result = self._parse_recognition_result(json.loads(content), subject)
                logger.info(f"照片识别成功: {len(result.get('knowledge_points', []))}个知识点")
                return result
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"识别结果解析失败: {e}")
                return {
                    "recognized_text": content[:500],
                    "latex": "",
                    "knowledge_points": [],
                    "difficulty": "medium",
                    "answer": "",
                    "solution_steps": [],
                    "question_type": "unknown",
                    "options": [],
                    "_raw": content,
                }

        except Exception as e:
            logger.error(f"Claude Vision 识别失败: {e}")
            return {"error": str(e)}

    def _parse_recognition_result(self, raw: Dict, subject: str) -> Dict:
        """标准化识别结果（支持多题 + 批改痕迹）"""
        questions = raw.get("questions", [])
        summary = raw.get("summary", {})

        if not questions:
            # 兼容旧格式（单题输出）
            return {
                "question_id": f"q_{self._generate_id(subject, raw.get('recognized_text', ''))}",
                "subject": subject,
                "recognized_text": raw.get("recognized_text", ""),
                "latex": raw.get("latex", ""),
                "knowledge_points": raw.get("knowledge_points", []),
                "difficulty": raw.get("difficulty", "medium"),
                "answer": raw.get("answer", ""),
                "solution_steps": raw.get("solution_steps", []),
                "question_type": raw.get("question_type", "unknown"),
                "options": raw.get("options", []),
                "batch": False,
                "summary": {},
            }

        # 多题批量识别 + 批改
        parsed_questions = []
        wrong_questions = []
        for q in questions:
            parsed = {
                "question_num": q.get("question_num", 0),
                "recognized_text": q.get("recognized_text", ""),
                "latex": q.get("latex", ""),
                "knowledge_points": q.get("knowledge_points", []),
                "difficulty": q.get("difficulty", "medium"),
                "standard_answer": q.get("standard_answer", ""),
                "solution_steps": q.get("solution_steps", []),
                "student_answer": q.get("student_answer", ""),
                "teacher_marks": q.get("teacher_marks", []),
                "is_correct": q.get("is_correct", True),
                "comment": q.get("comment", ""),
                "options": q.get("options", []),
            }
            parsed_questions.append(parsed)
            if not q.get("is_correct", True):
                wrong_questions.append(parsed)

        return {
            "questions": parsed_questions,
            "wrong_questions": wrong_questions,
            "batch": True,
            "summary": {
                "total_questions": summary.get("total_questions", len(questions)),
                "correct_count": summary.get("correct_count", 0),
                "wrong_count": summary.get("wrong_count", 0),
                "wrong_question_nums": summary.get("wrong_questions", []),
                "score_estimate": summary.get("score_estimate", ""),
            },
        }

    @staticmethod
    def _generate_id(subject: str, text: str) -> str:
        """生成问题ID"""
        import hashlib
        hash_val = hashlib.md5(f"{subject}:{text[:50]}".encode()).hexdigest()[:8]
        return f"{subject}_{hash_val}"


# 预留 LaTeX-OCR 接口（未来可对接 Mathpix 等处理复杂公式）
class LatexOCREngine:
    """
    LaTeX-OCR 预留接口（V1.0 不实现）
    用于复杂公式识别，可对接 Mathpix 等 API
    """

    def __init__(self):
        logger.info("LaTeX-OCR 引擎初始化（预留接口，V1.0 未启用）")

    def recognize_latex(self, image_data: bytes) -> Dict:
        """识别图片中的 LaTeX 公式"""
        logger.warning("LaTeX-OCR 接口未实现，请使用 Claude Vision 替代")
        return {
            "latex": "",
            "confidence": 0,
            "note": "LaTeX-OCR 预留接口，V1.0 使用 Claude Vision 处理公式",
        }
