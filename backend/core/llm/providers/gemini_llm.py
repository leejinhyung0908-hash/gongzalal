"""Gemini API 기반 LLM 구현체 (google.genai SDK 사용)."""
import os
from typing import Any, Optional

from backend.core.llm.base import BaseLLM


class GeminiLLM(BaseLLM):
    """Google Gemini API를 사용하는 LLM 구현체.

    google-genai (신규 SDK) 사용. google-generativeai (구 SDK)는 deprecated.
    """

    def __init__(self, model_path: Optional[str] = None, **kwargs: Any):
        """Gemini LLM 초기화.

        Args:
            model_path: Gemini 모델명 (예: gemini-2.0-flash)
            **kwargs: 추가 설정
                - api_key: Gemini API 키 (미지정 시 GEMINI_API_KEY 사용)
        """
        if model_path is None:
            model_path = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

        super().__init__(model_path, **kwargs)
        self.api_key = kwargs.get("api_key") or os.getenv("GEMINI_API_KEY", "")
        self._client = None
        self._loaded = False

    def load(self) -> None:
        """Gemini 클라이언트를 초기화합니다."""
        if self._loaded and self._client is not None:
            return

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

        from google import genai

        self._client = genai.Client(api_key=self.api_key)
        self._loaded = True

    def unload(self) -> None:
        """클라이언트 참조를 해제합니다."""
        self._client = None
        self._loaded = False

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs: Any,
    ) -> str:
        """Gemini API로 텍스트를 생성합니다."""
        if not self.is_loaded():
            raise RuntimeError("모델이 로드되지 않았습니다. load()를 먼저 호출하세요.")

        from google.genai import types

        response_mime_type: Optional[str] = kwargs.pop("response_mime_type", None)
        kwargs.pop("timeout_sec", None)

        config_kwargs: dict = {
            "temperature": temperature,
            "top_p": top_p,
            "max_output_tokens": max_new_tokens,
            # gemini-2.5-flash 등 Thinking 모델에서 thinking 토큰이
            # max_output_tokens 예산을 소비하는 문제 방지
            "thinking_config": types.ThinkingConfig(thinking_budget=0),
        }
        if response_mime_type:
            config_kwargs["response_mime_type"] = response_mime_type

        try:
            response = self._client.models.generate_content(
                model=self.model_path,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            return (response.text or "").strip()
        except Exception as e:
            return f"생성 중 오류가 발생했습니다: {e}"

    def is_loaded(self) -> bool:
        """클라이언트 초기화 여부를 반환합니다."""
        return self._loaded and self._client is not None
