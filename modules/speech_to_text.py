"""
语音转文字模块
支持 Whisper 中英文语音识别
"""
import os
import tempfile
from pathlib import Path
from typing import Optional

from common.config import get_config
from common.logger import logger


class SpeechToTextEngine:
    """Whisper 语音识别引擎"""

    def __init__(self):
        cfg = get_config("whisper") or {}
        self.model_size = cfg.get("model_size", "small")
        self.device = cfg.get("device", "cpu")
        self.language = cfg.get("language", "zh")

        self._model = None
        logger.info(f"Whisper 引擎初始化: model={self.model_size}, device={self.device}")

    def _load_model(self):
        """懒加载 Whisper 模型"""
        if self._model is not None:
            return self._model

        try:
            import whisper
            model = whisper.load_model(self.model_size, device=self.device)
            self._model = model
            logger.info(f"Whisper {self.model_size} 模型加载成功")
            return model
        except ImportError:
            logger.error("whisper 模块未安装，请运行: pip install openai-whisper")
            return None

    def transcribe(
        self,
        audio_path: str = None,
        audio_data: bytes = None,
        language: str = None,
    ) -> Optional[str]:
        """
        转录语音为文字
        :param audio_path: 音频文件路径（wav/mp3）
        :param audio_data: 音频二进制数据
        :param language: 语言代码（zh/en，默认自动检测）
        :return: 转录文字
        """
        model = self._load_model()
        if model is None:
            return None

        lang = language or self.language

        try:
            # 如果有二进制数据，先写入临时文件
            if audio_data:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio_data)
                    temp_path = f.name
            elif audio_path:
                temp_path = audio_path
            else:
                logger.error("需要提供 audio_path 或 audio_data")
                return None

            result = model.transcribe(
                temp_path,
                language=lang,
                fp16=False,  # CPU 模式禁用 fp16
                verbose=False,
            )

            # 清理临时文件
            if audio_data and os.path.exists(temp_path):
                os.unlink(temp_path)

            text = result.get("text", "").strip()
            logger.info(f"语音识别成功: {len(text)} 字")
            return text

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            if audio_data and os.path.exists(temp_path):
                os.unlink(temp_path)
            return None

    def transcribe_short_audio(
        self,
        audio_data: bytes,
        language: str = None,
    ) -> Optional[str]:
        """
        转录短时音频（<30秒），优化内存使用
        """
        return self.transcribe(audio_data=audio_data, language=language)


# 全局单例
_speech_engine: Optional[SpeechToTextEngine] = None


def get_speech_engine() -> SpeechToTextEngine:
    """获取语音识别引擎单例"""
    global _speech_engine
    if _speech_engine is None:
        _speech_engine = SpeechToTextEngine()
    return _speech_engine
