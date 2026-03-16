"""EXAONE 모델 LLM 구현체."""
import gc
import os
import re
from pathlib import Path
from typing import Any, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from backend.core.llm.base import BaseLLM


class ExaoneLLM(BaseLLM):
    """EXAONE 모델을 사용하는 LLM 구현체.

    LGAI-EXAONE 시리즈 (2.4B, 7.8B) 지원
    - EXAONE-3.5-2.4B-Instruct
    - EXAONE-3.5-7.8B-Instruct
    """

    def __init__(self, model_path: Optional[str] = None, lora_adapter_path: Optional[str] = None, **kwargs: Any):
        """EXAONE LLM 초기화.

        Args:
            model_path: 모델 경로 또는 HuggingFace 모델 ID
                예: "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
            lora_adapter_path: LoRA 어댑터 경로 (선택사항)
                예: "artifacts/lora-adapters/exaone-success-stories"
            **kwargs: 추가 설정
                - load_in_4bit: 4-bit 양자화 사용 (기본값: True)
                - load_in_8bit: 8-bit 양자화 사용 (기본값: False)
                - torch_dtype: torch dtype (기본값: torch.float16)
                - device_map: device map (기본값: "auto")
                - trust_remote_code: trust remote code (기본값: True)
        """
        # 모델 경로 설정
        if model_path is None:
            # 기본값: 로컬 EXAONE 모델
            model_path = "artifacts/base-models/exaone"

        super().__init__(model_path, **kwargs)

        # LoRA 어댑터 경로 저장
        self.lora_adapter_path = lora_adapter_path

        # 기본 설정
        self.load_in_4bit = kwargs.get("load_in_4bit", True)
        self.load_in_8bit = kwargs.get("load_in_8bit", False)
        self.torch_dtype = kwargs.get("torch_dtype", torch.float16)
        self.device_map = kwargs.get("device_map", "auto")
        self.trust_remote_code = kwargs.get("trust_remote_code", True)

        self._model = None
        self._tokenizer = None
        self._pipeline = None

    def load(self) -> None:
        """모델을 메모리에 로드합니다.

        RAM 최적화:
        - low_cpu_mem_usage=True: shard별 로드 (전체 모델을 한 번에 RAM에 올리지 않음)
        - torch_dtype=float16: FP32 대신 FP16으로 가중치 로드 (RAM 절반)
        - GC + CUDA 캐시 정리: 로드 후 즉시 임시 메모리 해제
        """
        if self.is_loaded():
            print(f"[ExaoneLLM] 모델이 이미 로드되어 있습니다: {self.model_path}")
            return

        print(f"[ExaoneLLM] 모델 로드 시작: {self.model_path}", flush=True)

        # 로드 전 메모리 정리
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        try:
            # 양자화 설정
            model_kwargs = {
                "device_map": self.device_map,
                "trust_remote_code": self.trust_remote_code,
                "low_cpu_mem_usage": True,       # ★ shard별 로드 → 피크 RAM 대폭 절감
                "torch_dtype": torch.float16,    # ★ FP16으로 로드 (FP32 대비 RAM 절반)
            }

            if self.load_in_4bit:
                try:
                    from transformers import BitsAndBytesConfig
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                    )
                    model_kwargs["quantization_config"] = quantization_config
                    print("[ExaoneLLM] 4-bit NF4 양자화 활성화 (low_cpu_mem_usage=True)", flush=True)
                except ImportError:
                    print(
                        "[ExaoneLLM] bitsandbytes가 설치되지 않아 4-bit 양자화를 건너뜁니다.",
                        flush=True,
                    )
            elif self.load_in_8bit:
                model_kwargs["load_in_8bit"] = True
                print("[ExaoneLLM] 8-bit 양자화 활성화", flush=True)

            # 모델 로드
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                **model_kwargs,
            )

            # ★ 로드 직후 임시 CPU 메모리 즉시 해제
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            print(f"[ExaoneLLM] 모델 로드 완료: {self.model_path}", flush=True)

            # LoRA 어댑터가 있으면 로드
            if self.lora_adapter_path:
                from peft import PeftModel
                lora_path = Path(self.lora_adapter_path)
                if lora_path.exists():
                    print(f"[ExaoneLLM] LoRA 어댑터 로드 시작: {lora_path}", flush=True)
                    self._model = PeftModel.from_pretrained(
                        self._model,
                        str(lora_path),
                    )
                    print(f"[ExaoneLLM] LoRA 어댑터 로드 완료: {lora_path}", flush=True)
                else:
                    print(f"[ExaoneLLM] 경고: LoRA 어댑터 경로를 찾을 수 없습니다: {lora_path}", flush=True)

            # 토크나이저 로드
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=self.trust_remote_code,
            )

            # 패딩 토큰 설정
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            # Pipeline 생성
            self._pipeline = pipeline(
                "text-generation",
                model=self._model,
                tokenizer=self._tokenizer,
            )
            print("[ExaoneLLM] Pipeline 생성 완료", flush=True)

            # 최종 메모리 상태 로깅
            if torch.cuda.is_available():
                vram_used = torch.cuda.memory_allocated(0) / (1024 ** 3)
                vram_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                print(
                    f"[ExaoneLLM] GPU VRAM: {vram_used:.1f}GB 사용 / {vram_total:.1f}GB 전체",
                    flush=True,
                )

        except Exception as e:
            print(f"[ExaoneLLM] 모델 로드 실패: {e}", flush=True)
            self._model = None
            self._tokenizer = None
            self._pipeline = None
            raise

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        **kwargs: Any,
    ) -> str:
        """텍스트를 생성합니다.

        Args:
            prompt: 입력 프롬프트
            max_new_tokens: 생성할 최대 토큰 수
            temperature: 생성 온도
            top_p: top-p 샘플링
            top_k: top-k 샘플링
            **kwargs: 추가 생성 파라미터

        Returns:
            생성된 텍스트
        """
        if not self.is_loaded():
            raise RuntimeError("모델이 로드되지 않았습니다. load()를 먼저 호출하세요.")

        try:
            # EXAONE 모델용 프롬프트 포맷
            # EXAONE은 instruction format을 사용
            formatted_prompt = f"[INST] {prompt} [/INST]"
            max_time = kwargs.pop("max_time", None)

            # 생성
            # 속도 우선을 위해 샘플링을 비활성화하고 greedy decoding을 사용합니다.
            outputs = self._pipeline(
                formatted_prompt,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                max_time=max_time,
                return_full_text=False,  # 프롬프트 제외하고 생성된 텍스트만
                **kwargs,
            )

            if outputs and len(outputs) > 0:
                generated_text = outputs[0]["generated_text"]
                return self._clean_response(generated_text)
            else:
                return "응답을 생성하지 못했습니다."

        except Exception as e:
            print(f"[ExaoneLLM] 생성 중 오류: {e}", flush=True)
            return f"생성 중 오류가 발생했습니다: {str(e)}"

    def _clean_response(self, text: str) -> str:
        """생성된 응답을 정리합니다."""
        # 불필요한 토큰 제거
        text = text.strip()

        # [/INST] 이후의 텍스트만 추출
        if "[/INST]" in text:
            text = text.split("[/INST]")[-1].strip()

        # [INST] 태그 제거
        text = re.sub(r"\[INST\].*?\[/INST\]", "", text, flags=re.DOTALL).strip()

        return text

    def is_loaded(self) -> bool:
        """모델이 로드되었는지 확인합니다."""
        return self._model is not None and self._pipeline is not None

    def unload(self) -> None:
        """모델을 메모리에서 언로드합니다."""
        # Pipeline → Model → Tokenizer 순서로 해제 (참조 역순)
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        # GC 강제 실행 후 GPU 캐시 정리
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        print(f"[ExaoneLLM] 모델 언로드 완료: {self.model_path}", flush=True)

    def get_model(self):
        """로드된 모델을 반환합니다."""
        return self._model

