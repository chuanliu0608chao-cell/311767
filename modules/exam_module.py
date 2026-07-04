"""
M6 出卷与阅卷模块
DeepSeek 生成试卷 + Claude Vision 批改答卷
"""
import json
import base64
from typing import Dict, List, Optional

from common.config import get_config
from common.logger import logger
from modules.diagnosis_engine import DiagnosisEngine
from modules.ocr_recognition import PhotoRecognitionEngine


class ExamGenerator:
    """试卷生成器"""

    def __init__(self, api_client=None):
        self.diagnosis_engine = DiagnosisEngine(api_client)

    def generate_exam(
        self,
        subject: str,
        grade: str,
        chapter: str = "",
        question_count: int = 20,
        difficulty_distribution: Dict = None,
        include_answer: bool = True,
    ) -> Dict:
        """
        生成试卷
        :return: 试卷数据
        """
        result = self.diagnosis_engine.generate_diagnosis(
            subject=subject,
            grade=grade,
            chapter=chapter,
            question_count=question_count,
        )

        if "error" in result:
            logger.error(f"试卷生成失败: {result['error']}")
            return result

        # 标准化输出
        exam_id = f"exam_{subject}_{grade[:2]}_{len(result.get('questions', []))}"
        total_score = sum(q.get("score", 5) for q in result.get("questions", []))

        return {
            "exam_id": exam_id,
            "subject": subject,
            "grade": grade,
            "chapter": chapter or "综合",
            "total_questions": len(result.get("questions", [])),
            "total_score": total_score or 100,
            "questions": result.get("questions", []),
            "include_answer": include_answer,
        }


class ExamGrader:
    """答卷批改器（Claude Vision）"""

    def __init__(self, api_client=None):
        self.ocr_engine = PhotoRecognitionEngine(api_client)
        ai_cfg = get_config("ai") or {}
        claude_cfg = ai_cfg.get("claude", {})
        self.claude_config = {
            "base_url": claude_cfg.get("base_url", "http://127.0.0.1:15721"),
            "model": claude_cfg.get("model", "claude-sonnet-4-6"),
            "max_tokens": claude_cfg.get("max_tokens", 3000),
            "temperature": claude_cfg.get("temperature", 0.1),
        }

    def grade_exam(
        self,
        exam_id: str,
        image_data: bytes,
        exam_questions: List[Dict],
    ) -> Dict:
        """
        批改答卷（上传答卷图片给 Claude Vision 批改）
        :param exam_id: 试卷ID
        :param image_data: 答卷图片
        :param exam_questions: 原题列表（用于比对）
        :return: 批改结果
        """
        logger.info(f"开始批改答卷: exam_id={exam_id}, 题目数={len(exam_questions)}")

        # 构建批改 Prompt
        questions_json = json.dumps(exam_questions, ensure_ascii=False, indent=2)
        prompt = f"""请批改这份答卷。

试卷ID: {exam_id}
题目列表:
{questions_json}

请逐题批改，给出每道题的得分和评语，并计算总分。

按以下 JSON 格式输出：
{{
    "exam_id": "{exam_id}",
    "total_score": 85,
    "question_scores": [
        {{
            "question_id": 1,
            "student_answer": "学生答案",
            "correct_answer": "正确答案",
            "score": 5,
            "full_score": 5,
            "is_correct": true,
            "comment": "评语"
        }}
    ]
}}"""

        # 编码为 base64
        b64_image = base64.b64encode(image_data).decode("utf-8")

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}",
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
            resp = self.ocr_engine.client.post(
                f"{self.claude_config['base_url']}/chat/completions",
                json_data={
                    "model": self.claude_config["model"],
                    "messages": messages,
                    "max_tokens": self.claude_config["max_tokens"],
                    "temperature": self.claude_config["temperature"],
                },
            )

            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")

            try:
                if "```" in content:
                    content = content.split("```")[1].replace("json", "").strip()
                result = json.loads(content)
                logger.info(f"批改完成: 总分{result.get('total_score', 0)}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"批改结果解析失败: {e}")
                return {"error": "批改结果解析失败", "raw": content[:500]}

        except Exception as e:
            logger.error(f"批改失败: {e}")
            return {"error": str(e)}
