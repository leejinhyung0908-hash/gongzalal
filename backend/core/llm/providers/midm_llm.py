"""Mi:dm 모델 LLM 구현체."""
import os
import re
from pathlib import Path
from typing import Any, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.core.llm.base import BaseLLM


class MidmLLM(BaseLLM):
    """Mi:dm 모델을 사용하는 LLM 구현체."""

    def __init__(self, model_path: Optional[str] = None, **kwargs: Any):
        """Mi:dm LLM 초기화.

        Args:
            model_path: 모델 경로 (기본값: artifacts/base-models/midm)
            **kwargs: 추가 설정
                - torch_dtype: torch dtype (기본값: "auto")
                - device_map: device map (기본값: "auto")
                - trust_remote_code: trust remote code (기본값: True)
        """
        # 모델 경로 설정
        if model_path is None:
            from backend.config import settings
            model_path = settings.MIDM_MODEL_PATH

        super().__init__(model_path, **kwargs)

        # 기본 설정
        self.torch_dtype = kwargs.get("torch_dtype", "auto")
        self.device_map = kwargs.get("device_map", "auto")
        self.trust_remote_code = kwargs.get("trust_remote_code", True)

        self._model = None
        self._tokenizer = None

    def load(self) -> None:
        """모델을 메모리에 로드합니다."""
        if self.is_loaded():
            print(f"[MidmLLM] 모델이 이미 로드되어 있습니다: {self.model_path}")
            return

        model_path = Path(self.model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"모델 경로를 찾을 수 없습니다: {model_path}"
            )

        print(f"[MidmLLM] 모델 로드 시작: {model_path}", flush=True)

        try:
            # 모델 로드
            self._model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                torch_dtype=self.torch_dtype,
                device_map=self.device_map,
                trust_remote_code=self.trust_remote_code,
            )

            # 토크나이저 로드
            self._tokenizer = AutoTokenizer.from_pretrained(str(model_path))

            print(f"[MidmLLM] 모델 로드 완료: {model_path}", flush=True)
        except Exception as e:
            print(f"[MidmLLM] 모델 로드 실패: {e}", flush=True)
            self._model = None
            self._tokenizer = None
            raise

    def unload(self) -> None:
        """모델을 메모리에서 해제합니다."""
        if self._model is not None:
            # GPU 메모리 해제
            if hasattr(self._model, "cpu"):
                self._model = self._model.cpu()
            del self._model
            self._model = None

        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        # Python 가비지 컬렉션 강제 실행
        import gc
        gc.collect()

        print(f"[MidmLLM] 모델 언로드 완료: {self.model_path}", flush=True)

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True,
        **kwargs: Any
    ) -> str:
        """텍스트를 생성합니다.

        Args:
            prompt: 입력 프롬프트
            max_new_tokens: 생성할 최대 토큰 수
            temperature: 생성 온도
            top_p: top-p 샘플링
            do_sample: 샘플링 사용 여부
            **kwargs: 추가 생성 파라미터

        Returns:
            생성된 텍스트
        """
        if not self.is_loaded():
            raise RuntimeError("모델이 로드되지 않았습니다. load()를 먼저 호출하세요.")

        try:
            # Mi:dm 모델은 chat template을 사용해야 함
            # 단순 텍스트가 아닌 경우 chat template 적용 시도
            formatted_prompt = prompt
            try:
                if hasattr(self._tokenizer, "apply_chat_template") and self._tokenizer.chat_template:
                    # 사용자 메시지로 변환
                    messages = [{"role": "user", "content": prompt}]
                    formatted_prompt = self._tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True
                    )
            except Exception as template_error:
                # Chat template 적용 실패 시 원본 프롬프트 사용
                print(f"[MidmLLM] Chat template 적용 실패, 원본 프롬프트 사용: {template_error}", flush=True)
                formatted_prompt = prompt

            # 프롬프트 토크나이징
            inputs = self._tokenizer(formatted_prompt, return_tensors="pt")

            # token_type_ids 제거 (모델이 사용하지 않는 경우)
            # BatchEncoding 객체를 딕셔너리로 변환하여 안전하게 제거
            inputs_dict = dict(inputs)
            inputs_dict.pop("token_type_ids", None)

            # GPU로 이동 (모델이 GPU에 있는 경우)
            if hasattr(self._model, "device"):
                inputs_dict = {k: v.to(self._model.device) for k, v in inputs_dict.items()}

            inputs = inputs_dict

            # 텍스트 생성
            with torch.no_grad():
                # EOS 토큰 ID 설정
                eos_token_id = self._tokenizer.eos_token_id
                pad_token_id = self._tokenizer.pad_token_id or eos_token_id

                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=do_sample,
                    eos_token_id=eos_token_id,
                    pad_token_id=pad_token_id,
                    **kwargs
                )

            # 생성된 텍스트 디코딩
            input_length = inputs["input_ids"].shape[1]
            generated_tokens = outputs[0][input_length:]

            # 빈 응답 체크
            if len(generated_tokens) == 0:
                print("[MidmLLM] 경고: 생성된 토큰이 없습니다.", flush=True)
                return "응답을 생성하지 못했습니다."

            generated_text = self._tokenizer.decode(
                generated_tokens,
                skip_special_tokens=True
            )

            # 불필요한 특수 토큰이나 접두사 제거
            # Mi:dm 모델의 경우 특수 토큰이 포함될 수 있음
            generated_text = generated_text.strip()

            # 빈 응답 체크
            if not generated_text:
                print("[MidmLLM] 경고: 디코딩된 텍스트가 비어있습니다.", flush=True)
                return "응답을 생성하지 못했습니다."

            # <|start_header_id|>assistant<|end_header_id|> 같은 패턴 제거
            if generated_text.startswith("<|start_header_id|>assistant<|end_header_id|>"):
                generated_text = generated_text.replace("<|start_header_id|>assistant<|end_header_id|>", "").strip()
            if generated_text.startswith("<|start_header_id|>"):
                # 헤더 부분 제거
                generated_text = re.sub(r"<\|start_header_id\|>.*?<\|end_header_id\|>\s*", "", generated_text, count=1).strip()

            # <|eot_id|> 같은 종료 토큰 제거
            generated_text = generated_text.replace("<|eot_id|>", "").strip()

            # 최종 빈 응답 체크
            if not generated_text:
                return "응답을 생성하지 못했습니다."

            return generated_text

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[MidmLLM] 텍스트 생성 실패: {e}", flush=True)
            print(f"[MidmLLM] 상세 오류:\n{error_details}", flush=True)
            raise

    def is_loaded(self) -> bool:
        """모델이 로드되었는지 확인합니다."""
        return self._model is not None and self._tokenizer is not None

