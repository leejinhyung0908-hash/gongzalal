"""QLoRA 채팅 서비스."""
import os
import re
from pathlib import Path
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

from backend.config import settings


class QLoRAChatService:
    """QLoRA 어댑터를 사용한 채팅 서비스."""

    def __init__(
        self,
        lora_adapter_path: Optional[str] = None,
        base_model_path: Optional[str] = None,
        load_in_4bit: bool = True,
        load_in_8bit: bool = False,
    ):
        """QLoRA 채팅 서비스 초기화.

        Args:
            lora_adapter_path: LoRA 어댑터 경로 (환경 변수 LORA_ADAPTER_PATH 또는 None)
            base_model_path: 기본 모델 경로 (기본값: artifacts/base-models/midm)
            load_in_4bit: 4-bit 양자화 사용 여부
            load_in_8bit: 8-bit 양자화 사용 여부
        """
        # 기본 모델 경로 설정
        if base_model_path is None:
            from backend.config import settings
            base_model_path = settings.MIDM_MODEL_PATH

        self.base_model_path = base_model_path
        self.lora_adapter_path = lora_adapter_path
        self.load_in_4bit = load_in_4bit
        self.load_in_8bit = load_in_8bit

        self._model = None
        self._tokenizer = None
        self._is_loaded = False

    def load(self) -> None:
        """모델과 LoRA 어댑터를 로드합니다."""
        if self._is_loaded:
            print("[QLoRAChatService] 모델이 이미 로드되어 있습니다.", flush=True)
            return

        base_path = Path(self.base_model_path)
        if not base_path.exists():
            raise FileNotFoundError(
                f"기본 모델 경로를 찾을 수 없습니다: {base_path}"
            )

        print(f"[QLoRAChatService] 기본 모델 로드 시작: {base_path}", flush=True)

        try:
            # 양자화 설정
            quantization_config = None
            if self.load_in_4bit:
                try:
                    from transformers import BitsAndBytesConfig
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                    )
                    print("[QLoRAChatService] 4-bit 양자화 활성화", flush=True)
                except ImportError:
                    print(
                        "[QLoRAChatService] bitsandbytes가 설치되지 않아 4-bit 양자화를 건너뜁니다.",
                        flush=True,
                    )
                    quantization_config = None
            elif self.load_in_8bit:
                try:
                    quantization_config = {"load_in_8bit": True}
                    print("[QLoRAChatService] 8-bit 양자화 활성화", flush=True)
                except Exception as e:
                    print(
                        f"[QLoRAChatService] 8-bit 양자화 설정 실패: {e}",
                        flush=True,
                    )
                    quantization_config = None

            # 기본 모델 로드
            model_kwargs = {
                "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
                "device_map": "auto",
                "trust_remote_code": True,
            }

            if quantization_config:
                if isinstance(quantization_config, dict):
                    model_kwargs.update(quantization_config)
                else:
                    model_kwargs["quantization_config"] = quantization_config

            self._model = AutoModelForCausalLM.from_pretrained(
                str(base_path),
                **model_kwargs,
            )

            # LoRA 어댑터가 있으면 로드
            if self.lora_adapter_path:
                lora_path = Path(self.lora_adapter_path)
                if lora_path.exists():
                    print(
                        f"[QLoRAChatService] LoRA 어댑터 로드 시작: {lora_path}",
                        flush=True,
                    )
                    self._model = PeftModel.from_pretrained(
                        self._model,
                        str(lora_path),
                    )
                    print(
                        "[QLoRAChatService] LoRA 어댑터 로드 완료",
                        flush=True,
                    )
                else:
                    print(
                        f"[QLoRAChatService] 경고: LoRA 어댑터 경로를 찾을 수 없습니다: {lora_path}",
                        flush=True,
                    )

            # 토크나이저 로드
            self._tokenizer = AutoTokenizer.from_pretrained(str(base_path))

            # 패딩 토큰 설정
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            self._is_loaded = True
            print("[QLoRAChatService] 모델 로드 완료", flush=True)

        except Exception as e:
            print(f"[QLoRAChatService] 모델 로드 실패: {e}", flush=True)
            self._model = None
            self._tokenizer = None
            self._is_loaded = False
            raise

    def unload(self) -> None:
        """모델을 메모리에서 해제합니다."""
        if self._model is not None:
            if hasattr(self._model, "cpu"):
                self._model = self._model.cpu()
            del self._model
            self._model = None

        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        self._is_loaded = False

        # Python 가비지 컬렉션 강제 실행
        import gc

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        print("[QLoRAChatService] 모델 언로드 완료", flush=True)

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True,
        **kwargs,
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
        if not self._is_loaded:
            raise RuntimeError(
                "모델이 로드되지 않았습니다. load()를 먼저 호출하세요."
            )

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
                print(f"[QLoRAChatService] Chat template 적용 실패, 원본 프롬프트 사용: {template_error}", flush=True)
                formatted_prompt = prompt

            # 프롬프트 토크나이징
            inputs = self._tokenizer(formatted_prompt, return_tensors="pt")

            # token_type_ids 제거
            inputs_dict = dict(inputs)
            inputs_dict.pop("token_type_ids", None)

            # GPU로 이동
            if hasattr(self._model, "device"):
                device = (
                    self._model.device
                    if hasattr(self._model, "device")
                    else next(self._model.parameters()).device
                )
                inputs_dict = {k: v.to(device) for k, v in inputs_dict.items()}

            inputs = inputs_dict

            # 텍스트 생성
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=do_sample,
                    pad_token_id=self._tokenizer.pad_token_id,
                    eos_token_id=self._tokenizer.eos_token_id,
                    **kwargs,
                )

            # 생성된 텍스트 디코딩
            input_length = inputs["input_ids"].shape[1]
            generated_tokens = outputs[0][input_length:]

            # 빈 응답 체크
            if len(generated_tokens) == 0:
                print("[QLoRAChatService] 경고: 생성된 토큰이 없습니다.", flush=True)
                return "응답을 생성하지 못했습니다."

            generated_text = self._tokenizer.decode(
                generated_tokens,
                skip_special_tokens=True,
            )

            # 불필요한 특수 토큰이나 접두사 제거
            # Mi:dm 모델의 경우 특수 토큰이 포함될 수 있음
            generated_text = generated_text.strip()

            # 빈 응답 체크
            if not generated_text:
                print("[QLoRAChatService] 경고: 디코딩된 텍스트가 비어있습니다.", flush=True)
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
            print(f"[QLoRAChatService] 텍스트 생성 실패: {e}", flush=True)
            print(f"[QLoRAChatService] 상세 오류:\n{error_details}", flush=True)
            raise

    def is_loaded(self) -> bool:
        """모델이 로드되었는지 확인합니다."""
        return self._is_loaded

