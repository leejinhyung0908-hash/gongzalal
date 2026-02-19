"""TTS (Text-to-Speech) 서비스.

Edge-TTS (Microsoft Azure 기반) 를 주 엔진으로 사용하고,
gTTS (Google Translate TTS) 를 폴백으로 사용합니다.

Edge-TTS 특징:
- 무료, API 키 불필요
- 고품질 한국어 Neural 음성 5종+
- async/await 네이티브
- 속도/피치 조절 가능

gTTS 특징:
- 무료, API 키 불필요
- 동기식 (스레드 풀 사용)
- 음질은 낮지만 안정적
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================================
# 한국어 음성 옵션
# ============================================================================

KOREAN_VOICES = {
    "female": "ko-KR-SunHiNeural",       # 여성 (밝고 명랑)
    "male": "ko-KR-InJoonNeural",         # 남성 (차분)
    "female2": "ko-KR-YuJinNeural",       # 여성2 (또렷)
    "male2": "ko-KR-HyunsuNeural",        # 남성2 (부드러움)
}

DEFAULT_VOICE = "female"

# 텍스트 분할 최대 길이 (Edge-TTS 안정성)
MAX_CHUNK_LENGTH = 3000


# ============================================================================
# 결과 데이터 클래스
# ============================================================================

@dataclass
class TTSResult:
    """TTS 변환 결과."""
    success: bool
    file_path: Optional[str] = None
    duration_seconds: Optional[int] = None
    file_size_bytes: Optional[int] = None
    voice_type: Optional[str] = None
    engine: Optional[str] = None  # "edge-tts" or "gtts"
    error: Optional[str] = None


# ============================================================================
# 텍스트 전처리
# ============================================================================

def _preprocess_text(text: str) -> str:
    """TTS에 적합하도록 텍스트를 전처리합니다.

    - 수식 기호, 특수문자 정리
    - 연속 공백/줄바꿈 정리
    - 번호 매기기 읽기 편하게 변환
    """
    if not text:
        return ""

    # Markdown 볼드/이탤릭 제거
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)

    # URL 제거
    text = re.sub(r"https?://\S+", "", text)

    # 특수 기호를 읽기 편한 형태로
    text = text.replace("→", "에서 ")
    text = text.replace("←", "으로부터 ")
    text = text.replace("⇒", "따라서 ")
    text = text.replace("※", "참고, ")
    text = text.replace("•", ", ")
    text = text.replace("·", ", ")

    # 연속 줄바꿈/공백 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    # 앞뒤 공백 제거
    text = text.strip()

    return text


def _split_text(text: str, max_length: int = MAX_CHUNK_LENGTH) -> list[str]:
    """긴 텍스트를 자연스러운 위치에서 분할합니다."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # 최대 길이 내에서 가장 좋은 분할점 찾기
        split_point = max_length

        # 우선순위: 줄바꿈 > 마침표 > 쉼표 > 공백
        for sep in ["\n\n", "\n", ". ", ", ", " "]:
            last_sep = remaining[:max_length].rfind(sep)
            if last_sep > max_length // 2:  # 너무 앞에서 자르지 않기
                split_point = last_sep + len(sep)
                break

        chunk = remaining[:split_point].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_point:].strip()

    return chunks


def _estimate_duration(text: str) -> int:
    """텍스트 길이로 대략적인 음성 재생 시간(초)을 추정합니다.

    한국어 자연 낭독 속도: ~250자/분
    """
    char_count = len(text)
    if char_count == 0:
        return 0
    return max(1, int(char_count / 250 * 60))


# ============================================================================
# Edge-TTS 엔진
# ============================================================================

async def _synthesize_edge_tts(
    text: str,
    output_path: str,
    voice: str = "ko-KR-SunHiNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> TTSResult:
    """Edge-TTS로 음성을 합성합니다.

    Args:
        text: 변환할 텍스트
        output_path: 저장할 MP3 파일 경로
        voice: 음성 이름
        rate: 속도 조절 (예: "+10%", "-10%")
        pitch: 피치 조절 (예: "+5Hz", "-5Hz")

    Returns:
        TTSResult
    """
    try:
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )

        await communicate.save(output_path)

        # 파일 크기 확인
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            return TTSResult(success=False, error="Edge-TTS: 빈 파일이 생성되었습니다.")

        duration = _estimate_duration(text)

        logger.info(
            f"[TTS] Edge-TTS 변환 완료: {file_size:,} bytes, "
            f"예상 {duration}초, voice={voice}"
        )

        return TTSResult(
            success=True,
            file_path=output_path,
            duration_seconds=duration,
            file_size_bytes=file_size,
            voice_type=voice,
            engine="edge-tts",
        )

    except Exception as e:
        logger.error(f"[TTS] Edge-TTS 변환 실패: {e}", exc_info=True)
        return TTSResult(success=False, error=f"Edge-TTS 오류: {str(e)}")


# ============================================================================
# gTTS 폴백 엔진
# ============================================================================

async def _synthesize_gtts(
    text: str,
    output_path: str,
) -> TTSResult:
    """gTTS로 음성을 합성합니다 (Edge-TTS 폴백용).

    gTTS는 동기식이므로 스레드 풀에서 실행합니다.
    """
    try:
        from gtts import gTTS

        def _run_gtts():
            tts = gTTS(text=text, lang="ko", slow=False)
            tts.save(output_path)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run_gtts)

        file_size = os.path.getsize(output_path)
        if file_size == 0:
            return TTSResult(success=False, error="gTTS: 빈 파일이 생성되었습니다.")

        duration = _estimate_duration(text)

        logger.info(
            f"[TTS] gTTS 폴백 변환 완료: {file_size:,} bytes, "
            f"예상 {duration}초"
        )

        return TTSResult(
            success=True,
            file_path=output_path,
            duration_seconds=duration,
            file_size_bytes=file_size,
            voice_type="gtts-ko",
            engine="gtts",
        )

    except Exception as e:
        logger.error(f"[TTS] gTTS 변환 실패: {e}", exc_info=True)
        return TTSResult(success=False, error=f"gTTS 오류: {str(e)}")


# ============================================================================
# 통합 TTS 서비스
# ============================================================================

class TTSService:
    """통합 TTS 서비스.

    Edge-TTS를 우선 사용하고, 실패 시 gTTS로 폴백합니다.
    """

    def __init__(self, audio_dir: str | Path = ""):
        """초기화.

        Args:
            audio_dir: MP3 파일 저장 디렉토리
        """
        if not audio_dir:
            audio_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "audio"

        self._audio_dir = Path(audio_dir)
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[TTS] 오디오 저장 경로: {self._audio_dir}")

    @property
    def audio_dir(self) -> Path:
        """오디오 저장 디렉토리."""
        return self._audio_dir

    def _generate_filename(
        self,
        commentary_id: int,
        voice_type: str,
        text_hash: str,
    ) -> str:
        """유일한 MP3 파일명을 생성합니다."""
        return f"commentary_{commentary_id}_{voice_type}_{text_hash}.mp3"

    async def synthesize(
        self,
        text: str,
        *,
        commentary_id: int,
        voice_type: str = DEFAULT_VOICE,
        rate: str = "+0%",
        force_regenerate: bool = False,
    ) -> TTSResult:
        """텍스트를 MP3 음성 파일로 변환합니다.

        Args:
            text: 변환할 텍스트 (해설 본문)
            commentary_id: 해설 ID (파일명에 사용)
            voice_type: 음성 타입 (female, male, female2, male2)
            rate: 읽기 속도 ("+0%", "+10%", "-10%" 등)
            force_regenerate: True면 기존 파일 무시하고 재생성

        Returns:
            TTSResult (success, file_path, duration, ...)
        """
        if not text or not text.strip():
            return TTSResult(success=False, error="변환할 텍스트가 비어있습니다.")

        # 1) 텍스트 전처리
        processed_text = _preprocess_text(text)
        if not processed_text:
            return TTSResult(success=False, error="전처리 후 텍스트가 비어있습니다.")

        # 2) 파일명 생성 (텍스트 해시 기반 → 동일 텍스트면 같은 파일)
        text_hash = hashlib.md5(processed_text.encode("utf-8")).hexdigest()[:8]
        filename = self._generate_filename(commentary_id, voice_type, text_hash)
        output_path = str(self._audio_dir / filename)

        # 3) 이미 존재하면 재사용 (중복 생성 방지)
        if not force_regenerate and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 0:
                logger.info(f"[TTS] 기존 파일 재사용: {filename} ({file_size:,} bytes)")
                return TTSResult(
                    success=True,
                    file_path=output_path,
                    duration_seconds=_estimate_duration(processed_text),
                    file_size_bytes=file_size,
                    voice_type=voice_type,
                    engine="cached",
                )

        # 4) 음성 이름 매핑
        edge_voice = KOREAN_VOICES.get(voice_type, KOREAN_VOICES[DEFAULT_VOICE])

        # 5) 텍스트 분할 처리 (긴 텍스트)
        chunks = _split_text(processed_text)

        if len(chunks) == 1:
            # 단일 청크 → 바로 변환
            result = await _synthesize_edge_tts(
                processed_text, output_path, voice=edge_voice, rate=rate
            )
            if not result.success:
                logger.warning("[TTS] Edge-TTS 실패, gTTS 폴백 시도...")
                result = await _synthesize_gtts(processed_text, output_path)

            return result

        else:
            # 다중 청크 → 개별 변환 후 합치기
            logger.info(f"[TTS] 긴 텍스트 분할: {len(chunks)}개 청크")
            return await self._synthesize_multi_chunk(
                chunks, output_path, edge_voice, rate
            )

    async def _synthesize_multi_chunk(
        self,
        chunks: list[str],
        output_path: str,
        voice: str,
        rate: str,
    ) -> TTSResult:
        """여러 청크를 개별 변환 후 하나의 MP3로 합칩니다."""
        temp_files = []
        total_size = 0

        try:
            for i, chunk in enumerate(chunks):
                temp_path = output_path.replace(".mp3", f"_part{i}.mp3")
                result = await _synthesize_edge_tts(chunk, temp_path, voice=voice, rate=rate)

                if not result.success:
                    result = await _synthesize_gtts(chunk, temp_path)

                if not result.success:
                    logger.error(f"[TTS] 청크 {i} 변환 실패, 건너뜀")
                    continue

                temp_files.append(temp_path)
                total_size += result.file_size_bytes or 0

            if not temp_files:
                return TTSResult(success=False, error="모든 청크 변환 실패")

            # MP3 파일 결합 (바이너리 연결 - MP3는 프레임 기반이라 가능)
            with open(output_path, "wb") as outfile:
                for temp_path in temp_files:
                    with open(temp_path, "rb") as infile:
                        outfile.write(infile.read())

            final_size = os.path.getsize(output_path)
            full_text = " ".join(chunks)
            duration = _estimate_duration(full_text)

            logger.info(
                f"[TTS] 다중 청크 합치기 완료: {len(temp_files)}개 → "
                f"{final_size:,} bytes, 예상 {duration}초"
            )

            return TTSResult(
                success=True,
                file_path=output_path,
                duration_seconds=duration,
                file_size_bytes=final_size,
                voice_type=voice,
                engine="edge-tts",
            )

        finally:
            # 임시 파일 정리
            for temp_path in temp_files:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except OSError:
                    pass

    async def synthesize_batch(
        self,
        items: list[dict],
        *,
        voice_type: str = DEFAULT_VOICE,
        rate: str = "+0%",
    ) -> list[TTSResult]:
        """여러 해설을 일괄 TTS 변환합니다.

        Args:
            items: [{"commentary_id": int, "text": str}, ...]
            voice_type: 음성 타입
            rate: 읽기 속도

        Returns:
            각 항목의 TTSResult 리스트
        """
        results = []
        total = len(items)

        for i, item in enumerate(items, 1):
            commentary_id = item.get("commentary_id", 0)
            text = item.get("text", "")

            logger.info(f"[TTS] 배치 진행: {i}/{total} (commentary_id={commentary_id})")

            result = await self.synthesize(
                text,
                commentary_id=commentary_id,
                voice_type=voice_type,
                rate=rate,
            )
            results.append(result)

        succeeded = sum(1 for r in results if r.success)
        logger.info(f"[TTS] 배치 완료: {succeeded}/{total} 성공")

        return results

    @staticmethod
    def get_available_voices() -> dict:
        """사용 가능한 한국어 음성 목록을 반환합니다."""
        return {
            k: {"voice_id": v, "description": _voice_description(k)}
            for k, v in KOREAN_VOICES.items()
        }


def _voice_description(voice_type: str) -> str:
    """음성 타입에 대한 설명을 반환합니다."""
    descriptions = {
        "female": "여성 (밝고 명랑한 톤)",
        "male": "남성 (차분한 톤)",
        "female2": "여성 (또렷한 톤)",
        "male2": "남성 (부드러운 톤)",
    }
    return descriptions.get(voice_type, voice_type)

