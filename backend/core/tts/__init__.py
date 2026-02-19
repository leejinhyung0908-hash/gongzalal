"""TTS (Text-to-Speech) 서비스 패키지.

Edge-TTS / gTTS 기반 한국어 음성 합성 모듈을 제공합니다.
"""

from backend.core.tts.tts_service import TTSService, TTSResult

__all__ = ["TTSService", "TTSResult"]

