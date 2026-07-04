"""
M8 英语口语模块
接收录音 → Whisper识别 → DeepSeek对话 → Edge TTS生成回复音频
"""
import io
import wave
from typing import Dict, Optional

from common.config import get_config
from common.logger import logger
from modules.diagnosis_engine import DiagnosisEngine


class EnglishDialogueEngine:
    """英语口语对话引擎"""

    def __init__(self, api_client=None):
        self.diagnosis_engine = DiagnosisEngine(api_client)

    def process_dialogue(
        self,
        audio_data: bytes,
        mode: str = "free_talk",
        topic: str = "",
    ) -> Dict:
        """
        处理英语口语对话
        :param audio_data: wav 格式录音
        :param mode: free_talk / listening_practice / role_play
        :param topic: 话题
        :return: 识别文本 + AI回复 + TTS音频
        """
        logger.info(f"英语口语对话: mode={mode}, topic={topic}")

        # Step 1: Whisper 识别（调用 Ubuntu 端 Whisper 服务）
        recognized_text = self._whisper_transcribe(audio_data)
        if not recognized_text:
            return {"error": "语音识别失败"}

        # Step 2: DeepSeek 生成回复
        ai_response = self._generate_response(recognized_text, mode, topic)

        # Step 3: Edge TTS 生成回复音频
        tts_audio_url = self._generate_tts(ai_response)

        # Step 4: 语法纠错
        correction = self._check_grammar(recognized_text)

        return {
            "recognized_text": recognized_text,
            "ai_response": ai_response,
            "tts_audio_url": tts_audio_url,
            "correction": correction,
            "mode": mode,
        }

    def _whisper_transcribe(self, audio_data: bytes) -> str:
        """调用 Whisper 识别语音"""
        try:
            from modules.speech_to_text import get_speech_engine
            engine = get_speech_engine()
            text = engine.transcribe_short_audio(audio_data, language="en")
            if text:
                return text
        except Exception as e:
            logger.warning(f"Whisper 识别失败，使用占位: {e}")
        logger.info("Whisper 识别不可用，返回占位数据")
        return "[语音识别结果]"

    def _generate_response(self, user_text: str, mode: str, topic: str) -> str:
        """DeepSeek 生成英文回复"""
        system_prompts = {
            "free_talk": "You are a friendly English conversation partner. Respond naturally to the student's message. Keep responses at an intermediate level.",
            "listening_practice": "You are an English teacher creating listening practice materials. Generate a short dialogue based on the topic.",
            "role_play": "You are acting out a scenario with the student. Stay in character and respond naturally.",
        }

        system_prompt = system_prompts.get(mode, system_prompts["free_talk"])
        if topic:
            system_prompt += f" Topic: {topic}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]

        try:
            resp = self.diagnosis_engine.client.post(
                f"{self.diagnosis_engine.config['base_url']}/chat/completions",
                json_data={
                    "model": self.diagnosis_engine.config["model"],
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 500,
                },
                headers={"Authorization": f"Bearer {self.diagnosis_engine.config['api_key']}"},
            )
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip()
        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            return "I'm sorry, I couldn't generate a response right now. Please try again later."

    def _generate_tts(self, text: str) -> str:
        """Edge TTS 生成音频"""
        # TODO: 实际调用 edge-tts 生成 wav 文件
        logger.info(f"TTS 生成（占位实现，待 edge-tts 部署后启用）: {text[:50]}...")
        return "/static/audio/tts_placeholder.wav"

    def _check_grammar(self, text: str) -> Optional[str]:
        """检查语法错误"""
        messages = [
            {
                "role": "system",
                "content": "You are an English grammar checker. Point out any grammatical errors in the student's text and suggest corrections. If there are no errors, return null.",
            },
            {"role": "user", "content": text},
        ]

        try:
            resp = self.diagnosis_engine.client.post(
                f"{self.diagnosis_engine.config['base_url']}/chat/completions",
                json_data={
                    "model": self.diagnosis_engine.config["model"],
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 200,
                },
                headers={"Authorization": f"Bearer {self.diagnosis_engine.config['api_key']}"},
            )
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return content if content.lower() not in ("null", "none", "") else None
        except Exception:
            return None
