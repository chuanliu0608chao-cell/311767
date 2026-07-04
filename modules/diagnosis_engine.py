"""
M1 智能诊断引擎
调用 DeepSeek 生成诊断题，支持多轮追问，输出行为指标
"""
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional

from common.config import get_config
from common.logger import logger
from common.api_client import ApiClient

# 诊断模板版本（预留字段）
TEMPLATE_VERSION = "1.0"


class DiagnosisEngine:
    """智能诊断引擎"""

    def __init__(self, api_client: Optional[ApiClient] = None):
        self.client = api_client or ApiClient()
        self.config = {
            "base_url": get_config("ai", "deepseek", "base_url", "https://api.deepseek.com/v1"),
            "model": get_config("ai", "deepseek", "model", "deepseek-chat"),
            "api_key": get_config("ai", "deepseek", "api_key", ""),
        }

    def generate_diagnosis_prompt(
        self,
        subject: str,
        grade: str,
        chapter: str = "",
        question_count: int = 20,
    ) -> str:
        """生成诊断题 Prompt"""
        subject_names = {
            "math": "数学",
            "chinese": "语文",
            "english": "英语",
            "physics": "物理",
            "chemistry": "化学",
        }
        subject_name = subject_names.get(subject, subject)

        prompt = f"""你是一位经验丰富的{grade}{subject_name}教师。请对学生的学习情况进行智能诊断。

要求：
1. 生成 {question_count} 道诊断题，覆盖{subject_name}的核心知识点
2. 难度分布：容易50%、中等30%、困难20%
3. 题型包括：选择题、填空题、计算题
4. 每道题标注对应的知识点
5. 每道题标注分值（总分100分）
6. 提供标准答案和简要解析

请按以下 JSON 格式输出（不要输出其他内容）：
{{
    "subject": "{subject}",
    "grade": "{grade}",
    "chapter": "{chapter or '综合'}",
    "total_questions": {question_count},
    "total_score": 100,
    "questions": [
        {{
            "id": 1,
            "type": "choice",
            "score": 5,
            "content": "题目内容",
            "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
            "answer": "A",
            "knowledge_point": "对应知识点",
            "difficulty": "easy",
            "explanation": "简要解析"
        }}
    ]
}}

注意：
- 如果是数学题，请使用 LaTeX 格式书写公式，例如 $x^2 + 2x + 1$
- 选择题必须有4个选项
- 填空题只需提供题干和答案
- 计算题需要完整的解题步骤"""

        if chapter:
            prompt = prompt.replace('"chapter": "综合"', f'"chapter": "{chapter}"')

        return prompt

    def generate_diagnosis(
        self,
        subject: str,
        grade: str,
        chapter: str = "",
        question_count: int = 20,
    ) -> Dict:
        """
        调用 DeepSeek 生成诊断题
        :return: 诊断题目列表
        """
        prompt = self.generate_diagnosis_prompt(subject, grade, chapter, question_count)

        messages = [
            {"role": "system", "content": "你是一位专业的{0}教师，擅长通过诊断题了解学生的学习情况。请严格按照要求的JSON格式输出。".format(subject)},
            {"role": "user", "content": prompt},
        ]

        logger.info(f"开始诊断出题: subject={subject}, grade={grade}, chapter={chapter}")

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

            # 解析 JSON
            try:
                # 尝试从 Markdown 代码块中提取 JSON
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

                result = json.loads(content)
                logger.info(f"诊断出题成功: {len(result.get('questions', []))} 道题")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"诊断题 JSON 解析失败: {e}")
                logger.debug(f"原始内容: {content[:500]}")
                return {"error": "AI 返回格式异常", "raw": content}

        except Exception as e:
            logger.error(f"诊断出题失败: {e}")
            return {"error": str(e)}

    def generate_follow_up(
        self,
        subject: str,
        question: Dict,
        student_answer: str,
        is_correct: bool,
        depth: int = 1,
    ) -> Dict:
        """
        多轮追问：根据学生答题情况生成追问
        :param subject: 学科
        :param question: 原题目
        :param student_answer: 学生答案
        :param is_correct: 是否正确
        :param depth: 追问深度（1-3）
        :return: 追问内容
        """
        if is_correct:
            system_prompt = (
                f"学生对这道{subject}题回答正确。请：\n"
                f"1. 给出简短鼓励\n"
                f"2. 如果深度<3，生成一道进阶追问（提高难度）\n"
                f"3. 如果已达最大深度，推荐一个相关知识点让学生巩固"
            )
        else:
            system_prompt = (
                f"学生对这道{subject}题回答错误。请：\n"
                f"1. 指出错误原因（温和地）\n"
                f"2. 给出正确思路引导\n"
                f"3. 如果深度<3，生成一道针对性追问（降低难度，聚焦薄弱点）\n"
                f"4. 如果已达最大深度，建议回到基础概念重新学习"
            )

        prompt = f"""原题：{question.get('content', '')}
学生答案：{student_answer}
正确答案：{question.get('answer', '')}
是否正确：{'正确' if is_correct else '错误'}
追问深度：{depth}/3

{system_prompt}

请按以下JSON格式输出：
{{
    "feedback": "对学生说的话",
    "guidance": "解题思路引导",
    "follow_up_question": "追问内容（如无则为null）",
    "follow_up_type": "advanced|targeted|none",
    "recommended_knowledge": "推荐学习的知识点"
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        logger.debug(f"多轮追问 (depth={depth}): subject={subject}")

        try:
            resp = self.client.post(
                f"{self.config['base_url']}/chat/completions",
                json_data={
                    "model": self.config["model"],
                    "messages": messages,
                    "temperature": 0.5,
                    "max_tokens": 1000,
                },
                headers={"Authorization": f"Bearer {self.config['api_key']}"},
            )
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")

            try:
                if "```" in content:
                    content = content.split("```")[1].replace("json", "").strip()
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                return {"feedback": content, "guidance": "", "follow_up_question": None, "follow_up_type": "none", "recommended_knowledge": ""}

        except Exception as e:
            logger.error(f"追问失败: {e}")
            return {
                "feedback": "暂时无法生成追问，请稍后再试",
                "guidance": "",
                "follow_up_question": None,
                "follow_up_type": "none",
                "recommended_knowledge": "",
            }

    def analyze_behavior_metrics(
        self,
        answers: List[Dict],
    ) -> Dict:
        """
        分析学生行为指标（客观数据，不打主观心理标签）
        :param answers: 答题记录列表，每项包含 question_id, is_correct, time_spent, skipped
        :return: 行为指标分析
        """
        total = len(answers)
        if total == 0:
            return {"error": "没有答题数据"}

        correct_count = sum(1 for a in answers if a.get("is_correct", False))
        wrong_count = sum(1 for a in answers if not a.get("is_correct", False) and not a.get("skipped", False))
        skipped_count = sum(1 for a in answers if a.get("skipped", False))
        accuracy = round(correct_count / total * 100, 1)

        # 计算平均答题时间
        times = [a.get("time_spent", 0) for a in answers if a.get("time_spent", 0) > 0]
        avg_time = round(sum(times) / len(times), 1) if times else 0

        # 按知识点统计正确率
        knowledge_stats = {}
        for a in answers:
            kp = a.get("knowledge_point", "unknown")
            if kp not in knowledge_stats:
                knowledge_stats[kp] = {"total": 0, "correct": 0}
            knowledge_stats[kp]["total"] += 1
            if a.get("is_correct", False):
                knowledge_stats[kp]["correct"] += 1

        for kp in knowledge_stats:
            ks = knowledge_stats[kp]
            ks["accuracy"] = round(ks["correct"] / ks["total"] * 100, 1)

        # 正确率波动分析（按顺序）
        correct_flags = [1 if a.get("is_correct", False) else 0 for a in answers]
        volatility = self._calculate_volatility(correct_flags)

        # 识别薄弱知识点（正确率 < 60%）
        weak_points = [
            kp for kp, stats in knowledge_stats.items()
            if stats["accuracy"] < 60 and stats["total"] >= 2
        ]

        result = {
            "template_version": TEMPLATE_VERSION,  # 预留字段
            "total_questions": total,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "skipped_count": skipped_count,
            "accuracy_percent": accuracy,
            "avg_time_per_question_sec": avg_time,
            "volatility": volatility,
            "knowledge_point_accuracy": knowledge_stats,
            "weak_points": weak_points[:5],  # 最多5个薄弱知识点
            "strong_points": [
                kp for kp, stats in knowledge_stats.items()
                if stats["accuracy"] >= 80 and stats["total"] >= 2
            ][:5],
        }

        logger.info(f"行为指标分析完成: 正确率{accuracy}%, 薄弱点{len(weak_points)}个")
        return result

    @staticmethod
    def _calculate_volatility(flags: List[int]) -> Dict:
        """计算正确率波动"""
        if len(flags) < 4:
            return {"level": "insufficient_data", "description": "数据不足"}

        # 滑动窗口（5题）正确率
        window = 5
        rates = []
        for i in range(len(flags) - window + 1):
            window_flags = flags[i:i + window]
            rate = sum(window_flags) / len(window_flags) * 100
            rates.append(rate)

        if not rates:
            return {"level": "stable", "description": "表现稳定"}

        max_rate = max(rates)
        min_rate = min(rates)
        spread = max_rate - min_rate

        if spread <= 20:
            level = "stable"
            desc = "表现稳定"
        elif spread <= 40:
            level = "moderate"
            desc = "有波动，注意知识盲区"
        else:
            level = "volatile"
            desc = "波动较大，建议系统复习"

        return {
            "level": level,
            "spread_percent": round(spread, 1),
            "description": desc,
            "window_rates": [round(r, 1) for r in rates],
        }
