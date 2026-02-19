"""중앙 MCP 서버.

모든 모델(KoELECTRA, EXAONE)을 중앙에서 로드하고 관리합니다.
Orchestrator와 Agent는 MCP 클라이언트를 통해 이 서버의 툴을 호출합니다.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from fastmcp import FastMCP
    _FASTMCP_AVAILABLE = True
except ImportError:
    _FASTMCP_AVAILABLE = False
    FastMCP = None

from backend.config import settings
from backend.core.llm.providers.exaone_llm import ExaoneLLM

logger = logging.getLogger(__name__)

# ============================================================================
# KoELECTRA 유틸리티 함수들
# ============================================================================

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from peft import PeftModel
    import torch
    _KOELECTRA_AVAILABLE = True
except ImportError:
    _KOELECTRA_AVAILABLE = False

# 레이블 매핑
GATEWAY_LABELS = {"BLOCK": 0, "POLICY_BASED": 1, "RULE_BASED": 2}
LABEL_TO_GATEWAY = {v: k for k, v in GATEWAY_LABELS.items()}
INTENT_LABELS = {"DB_QUERY": 0, "EXPLAIN": 1, "ADVICE": 2, "OUT_OF_DOMAIN": 3}
LABEL_TO_INTENT = {v: k for k, v in INTENT_LABELS.items()}

SPAM_PROB_LOW = 0.35
SPAM_PROB_HIGH = 0.75


class ExamCentralMCPServer:
    """Exam 도메인 중앙 MCP 서버.

    Exam 도메인 전용 LLM 모델과 툴을 중앙에서 관리합니다.
    """

    _instance: Optional["ExamCentralMCPServer"] = None
    _initialized: bool = False

    def __new__(cls):
        """싱글톤 패턴."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """ExamCentralMCPServer 초기화."""
        if self._initialized:
            return

        logger.info("[Exam 중앙 MCP 서버] 초기화 시작")

        # FastMCP 서버 생성
        self.mcp = FastMCP(name="exam_central_mcp_server")

        # 모델 인스턴스 (지연 로딩)
        self.koelectra_spam_filter_model: Optional[Any] = None
        self.koelectra_spam_filter_tokenizer: Optional[Any] = None
        self.koelectra_gateway_classifier_model: Optional[Any] = None
        self.koelectra_gateway_classifier_tokenizer: Optional[Any] = None
        self.koelectra_intent_classifier_model: Optional[Any] = None
        self.koelectra_intent_classifier_tokenizer: Optional[Any] = None
        self.exaone_model: Optional[ExaoneLLM] = None

        # 툴 저장소 (직접 호출용)
        self._tools: Dict[str, Any] = {}

        # 툴 설정
        self._setup_koelectra_tools()
        self._setup_exaone_tools()
        self._setup_integrated_tools()

        self._initialized = True
        logger.info("[Exam 중앙 MCP 서버] 초기화 완료")

    def _load_koelectra_spam_filter(self) -> tuple:
        """KoELECTRA 스팸 필터 모델을 로드합니다."""
        if self.koelectra_spam_filter_model is not None:
            return self.koelectra_spam_filter_model, self.koelectra_spam_filter_tokenizer

        if not _KOELECTRA_AVAILABLE:
            logger.warning("[Exam 중앙 MCP 서버] KoELECTRA가 설치되지 않았습니다.")
            return None, None

        try:
            model_path = os.getenv("SPAM_FILTER_MODEL_PATH") or settings.KOELECTRA_SPAM_LORA_PATH
            base_model_name = settings.KOELECTRA_BASE_MODEL

            if not model_path or not Path(model_path).exists():
                logger.warning(f"[Exam 중앙 MCP 서버] 스팸 필터 모델 경로를 찾을 수 없습니다: {model_path}")
                return None, None

            logger.info(f"[Exam 중앙 MCP 서버] 스팸 필터 모델 로드 중: {model_path}")

            adapter_config = Path(model_path) / "adapter_config.json"
            is_lora = adapter_config.exists()

            if is_lora:
                self.koelectra_spam_filter_tokenizer = AutoTokenizer.from_pretrained(model_path)
                base_model = AutoModelForSequenceClassification.from_pretrained(base_model_name, num_labels=2)
                self.koelectra_spam_filter_model = PeftModel.from_pretrained(base_model, model_path)
            else:
                self.koelectra_spam_filter_tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.koelectra_spam_filter_model = AutoModelForSequenceClassification.from_pretrained(model_path)

            self.koelectra_spam_filter_model.eval()
            if torch.cuda.is_available():
                self.koelectra_spam_filter_model = self.koelectra_spam_filter_model.cuda()

            logger.info("[Exam 중앙 MCP 서버] 스팸 필터 모델 로드 완료")
            return self.koelectra_spam_filter_model, self.koelectra_spam_filter_tokenizer
        except Exception as e:
            logger.error(f"[Exam 중앙 MCP 서버] 스팸 필터 모델 로드 실패: {e}", exc_info=True)
            return None, None

    def _load_koelectra_gateway_classifier(self) -> tuple:
        """KoELECTRA 게이트웨이 분류기 모델을 로드합니다."""
        if self.koelectra_gateway_classifier_model is not None:
            return self.koelectra_gateway_classifier_model, self.koelectra_gateway_classifier_tokenizer

        if not _KOELECTRA_AVAILABLE:
            logger.warning("[Exam 중앙 MCP 서버] KoELECTRA가 설치되지 않았습니다.")
            return None, None

        try:
            model_path = os.getenv("KOELECTRA_GATEWAY_LORA_PATH") or settings.KOELECTRA_GATEWAY_LORA_PATH
            base_model_name = settings.KOELECTRA_BASE_MODEL

            if not model_path or not Path(model_path).exists():
                logger.warning(f"[Exam 중앙 MCP 서버] 게이트웨이 분류기 모델 경로를 찾을 수 없습니다: {model_path}")
                return None, None

            logger.info(f"[Exam 중앙 MCP 서버] 게이트웨이 분류기 모델 로드 중: {model_path}")

            adapter_config = Path(model_path) / "adapter_config.json"
            is_lora = adapter_config.exists()

            if is_lora:
                self.koelectra_gateway_classifier_tokenizer = AutoTokenizer.from_pretrained(model_path)
                base_model = AutoModelForSequenceClassification.from_pretrained(base_model_name, num_labels=3)
                self.koelectra_gateway_classifier_model = PeftModel.from_pretrained(base_model, model_path)
            else:
                self.koelectra_gateway_classifier_tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.koelectra_gateway_classifier_model = AutoModelForSequenceClassification.from_pretrained(model_path)

            self.koelectra_gateway_classifier_model.eval()
            if torch.cuda.is_available():
                self.koelectra_gateway_classifier_model = self.koelectra_gateway_classifier_model.cuda()

            logger.info("[Exam 중앙 MCP 서버] 게이트웨이 분류기 모델 로드 완료")
            return self.koelectra_gateway_classifier_model, self.koelectra_gateway_classifier_tokenizer
        except Exception as e:
            logger.error(f"[Exam 중앙 MCP 서버] 게이트웨이 분류기 모델 로드 실패: {e}", exc_info=True)
            return None, None

    def _load_koelectra_intent_classifier(self) -> tuple:
        """KoELECTRA 의도 분류기 모델을 로드합니다."""
        if self.koelectra_intent_classifier_model is not None:
            return self.koelectra_intent_classifier_model, self.koelectra_intent_classifier_tokenizer

        if not _KOELECTRA_AVAILABLE:
            logger.warning("[Exam 중앙 MCP 서버] KoELECTRA가 설치되지 않았습니다.")
            return None, None

        try:
            model_path = os.getenv("KOELECTRA_INTENT_LORA_PATH") or settings.KOELECTRA_INTENT_LORA_PATH
            base_model_name = settings.KOELECTRA_BASE_MODEL

            if not model_path or not Path(model_path).exists():
                logger.warning(f"[Exam 중앙 MCP 서버] 의도 분류기 모델 경로를 찾을 수 없습니다: {model_path}")
                return None, None

            logger.info(f"[Exam 중앙 MCP 서버] 의도 분류기 모델 로드 중: {model_path}")

            adapter_config = Path(model_path) / "adapter_config.json"
            is_lora = adapter_config.exists()

            if is_lora:
                self.koelectra_intent_classifier_tokenizer = AutoTokenizer.from_pretrained(model_path)
                base_model = AutoModelForSequenceClassification.from_pretrained(base_model_name, num_labels=4)
                self.koelectra_intent_classifier_model = PeftModel.from_pretrained(base_model, model_path)
            else:
                self.koelectra_intent_classifier_tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.koelectra_intent_classifier_model = AutoModelForSequenceClassification.from_pretrained(model_path)

            self.koelectra_intent_classifier_model.eval()
            if torch.cuda.is_available():
                self.koelectra_intent_classifier_model = self.koelectra_intent_classifier_model.cuda()

            logger.info("[Exam 중앙 MCP 서버] 의도 분류기 모델 로드 완료")
            return self.koelectra_intent_classifier_model, self.koelectra_intent_classifier_tokenizer
        except Exception as e:
            logger.error(f"[Exam 중앙 MCP 서버] 의도 분류기 모델 로드 실패: {e}", exc_info=True)
            return None, None

    def _load_exaone_model(self) -> Optional[ExaoneLLM]:
        """EXAONE 모델을 로드합니다."""
        if self.exaone_model is not None:
            return self.exaone_model

        try:
            # 프로젝트 루트 찾기
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent

            # EXAONE 베이스 모델 경로
            base_model_path = settings.EXAONE_BASE_MODEL_PATH
            base_model_path_obj = Path(base_model_path)

            if not base_model_path_obj.is_absolute():
                base_model_path = project_root / base_model_path_obj
            else:
                base_model_path = base_model_path_obj

            if not base_model_path.exists():
                logger.warning(f"[Exam 중앙 MCP 서버] EXAONE 모델 경로를 찾을 수 없습니다: {base_model_path}")
                base_model_path = project_root / "artifacts" / "base-models" / "exaone"

            # LoRA 어댑터 경로
            lora_path = os.getenv(
                "EXAONE_SUCCESS_STORIES_LORA_PATH",
                "artifacts/lora-adapters/exaone-success-stories"
            )
            lora_path_obj = Path(lora_path)

            if not lora_path_obj.is_absolute():
                lora_path_obj = project_root / lora_path_obj

            if not lora_path_obj.exists():
                logger.info(f"[Exam 중앙 MCP 서버] LoRA 어댑터 경로를 찾을 수 없습니다: {lora_path_obj}. 기본 모델만 사용합니다.")
                lora_path = None
            else:
                lora_path = str(lora_path_obj)

            logger.info(f"[Exam 중앙 MCP 서버] EXAONE 모델 로드 중: {base_model_path}")

            self.exaone_model = ExaoneLLM(
                model_path=str(base_model_path),
                lora_adapter_path=lora_path,
                load_in_4bit=True,
            )

            logger.info("[Exam 중앙 MCP 서버] EXAONE 모델 로드 완료")
            return self.exaone_model
        except Exception as e:
            logger.error(f"[Exam 중앙 MCP 서버] EXAONE 모델 로드 실패: {e}", exc_info=True)
            return None

    def _setup_koelectra_tools(self) -> None:
        """KoELECTRA 모델을 위한 FastMCP 툴을 설정합니다.

        NOTE: @self.mcp.tool() 데코레이터는 함수를 FunctionTool로 래핑합니다.
        직접 호출이 필요하므로 원본 함수 참조를 _tools에 먼저 저장한 후 MCP에 등록합니다.
        """

        # ── 게이트웨이 분류기 ──
        def _classify_gateway_fn(text: str) -> dict:
            """KoELECTRA 게이트웨이 분류기: 텍스트를 BLOCK/POLICY_BASED/RULE_BASED로 분류합니다."""
            try:
                model, tokenizer = self._load_koelectra_gateway_classifier()
                if model is None or tokenizer is None:
                    return {
                        "predicted_label": 1,
                        "gateway": "POLICY_BASED",
                        "confidence": 0.5,
                        "probabilities": [0.33, 0.34, 0.33],
                        "method": "unavailable",
                    }

                inputs = tokenizer(text, truncation=True, max_length=256, padding=True, return_tensors="pt")
                if torch.cuda.is_available():
                    inputs = {k: v.cuda() for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=-1)

                prob_list = probs[0].cpu().tolist()
                predicted_label = int(torch.argmax(probs[0]).item())
                confidence = float(prob_list[predicted_label])
                gateway = LABEL_TO_GATEWAY.get(predicted_label, "POLICY_BASED")

                return {
                    "predicted_label": predicted_label,
                    "gateway": gateway,
                    "confidence": confidence,
                    "probabilities": prob_list,
                    "method": "koelectra_gateway",
                }
            except Exception as e:
                logger.error(f"[Exam 중앙 MCP 서버] 게이트웨이 분류 오류: {e}", exc_info=True)
                return {
                    "predicted_label": 1,
                    "gateway": "POLICY_BASED",
                    "confidence": 0.5,
                    "probabilities": [0.33, 0.34, 0.33],
                    "method": "error",
                    "error": str(e),
                }

        # ── 의도 분류기 ──
        def _classify_intent_fn(text: str) -> dict:
            """KoELECTRA 의도 분류기: 텍스트의 의도를 DB_QUERY/EXPLAIN/ADVICE/OUT_OF_DOMAIN으로 분류합니다."""
            try:
                model, tokenizer = self._load_koelectra_intent_classifier()
                if model is None or tokenizer is None:
                    return {
                        "predicted_label": 0,
                        "intent": "DB_QUERY",
                        "confidence": 0.5,
                        "probabilities": [0.25, 0.25, 0.25, 0.25],
                        "method": "unavailable",
                    }

                inputs = tokenizer(text, truncation=True, max_length=256, padding=True, return_tensors="pt")
                if torch.cuda.is_available():
                    inputs = {k: v.cuda() for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=-1)

                prob_list = probs[0].cpu().tolist()
                predicted_label = int(torch.argmax(probs[0]).item())
                confidence = float(prob_list[predicted_label])
                intent = LABEL_TO_INTENT.get(predicted_label, "DB_QUERY")

                return {
                    "predicted_label": predicted_label,
                    "intent": intent,
                    "confidence": confidence,
                    "probabilities": prob_list,
                    "method": "koelectra_intent",
                }
            except Exception as e:
                logger.error(f"[Exam 중앙 MCP 서버] 의도 분류 오류: {e}", exc_info=True)
                return {
                    "predicted_label": 0,
                    "intent": "DB_QUERY",
                    "confidence": 0.5,
                    "probabilities": [0.25, 0.25, 0.25, 0.25],
                    "method": "error",
                    "error": str(e),
                }

        # ── 스팸 필터 ──
        def _filter_spam_fn(text: str) -> dict:
            """KoELECTRA 스팸 필터: 텍스트가 스팸인지 판단합니다."""
            try:
                model, tokenizer = self._load_koelectra_spam_filter()
                if model is None or tokenizer is None:
                    return {
                        "spam_prob": 0.5,
                        "label": "uncertain",
                        "confidence": "low",
                        "method": "unavailable",
                        "threshold_zone": "ambiguous",
                    }

                inputs = tokenizer(text, truncation=True, max_length=256, padding=True, return_tensors="pt")
                if torch.cuda.is_available():
                    inputs = {k: v.cuda() for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=-1)

                spam_prob = float(probs[0][1].item()) if probs.shape[1] > 1 else 0.0

                if spam_prob < SPAM_PROB_LOW:
                    threshold_zone = "low"
                    label = "ham"
                    confidence = "high" if spam_prob < 0.2 else "medium"
                elif spam_prob > SPAM_PROB_HIGH:
                    threshold_zone = "high"
                    label = "spam"
                    confidence = "high" if spam_prob > 0.9 else "medium"
                else:
                    threshold_zone = "ambiguous"
                    label = "uncertain"
                    confidence = "medium"

                return {
                    "spam_prob": spam_prob,
                    "label": label,
                    "confidence": confidence,
                    "method": "koelectra",
                    "threshold_zone": threshold_zone,
                }
            except Exception as e:
                logger.error(f"[Exam 중앙 MCP 서버] 스팸 필터 오류: {e}", exc_info=True)
                return {
                    "spam_prob": 0.5,
                    "label": "uncertain",
                    "confidence": "low",
                    "method": "error",
                    "error": str(e),
                }

        # 원본 함수를 _tools에 저장 (직접 호출용)
        self._tools["classify_gateway"] = _classify_gateway_fn
        self._tools["classify_intent"] = _classify_intent_fn
        self._tools["filter_spam"] = _filter_spam_fn

        # FastMCP 툴로도 등록 (MCP 클라이언트용)
        self.mcp.tool(name="classify_gateway")(_classify_gateway_fn)
        self.mcp.tool(name="classify_intent")(_classify_intent_fn)
        self.mcp.tool(name="filter_spam")(_filter_spam_fn)

        logger.info("[Exam 중앙 MCP 서버] KoELECTRA 툴 설정 완료")

    def _setup_exaone_tools(self) -> None:
        """EXAONE 모델을 위한 FastMCP 툴을 설정합니다."""

        def _exaone_generate_text_fn(
            prompt: str,
            max_new_tokens: int = 512,
            temperature: float = 0.7,
            top_p: float = 0.9,
            top_k: int = 50
        ) -> dict:
            """EXAONE 모델을 사용하여 텍스트를 생성합니다."""
            try:
                exaone = self._load_exaone_model()
                if exaone is None:
                    return {
                        "success": False,
                        "error": "EXAONE 모델을 로드할 수 없습니다.",
                        "text": "",
                    }

                if not exaone.is_loaded():
                    exaone.load()

                generated_text = exaone.generate(
                    prompt=prompt,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                )

                return {
                    "success": True,
                    "text": generated_text,
                    "prompt": prompt,
                }
            except Exception as e:
                logger.error(f"[Exam 중앙 MCP 서버] EXAONE 생성 오류: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "text": "",
                }

        def _exaone_analyze_exam_question_fn(
            question: str,
            context: Optional[str] = None,
            max_new_tokens: int = 512
        ) -> dict:
            """EXAONE 모델을 사용하여 시험 문제를 분석합니다."""
            try:
                exaone = self._load_exaone_model()
                if exaone is None:
                    return {
                        "success": False,
                        "error": "EXAONE 모델을 로드할 수 없습니다.",
                    }

                if not exaone.is_loaded():
                    exaone.load()

                # 프롬프트 구성
                if context:
                    prompt = f"""다음 공무원 시험 문제를 분석하고 전문적인 답변을 제공해주세요.

문제: {question}

추가 컨텍스트:
{context}

위 정보를 바탕으로 질문자에게 도움이 되는 상세한 분석을 제공해주세요."""
                else:
                    prompt = f"""다음 공무원 시험 문제를 분석하고 전문적인 답변을 제공해주세요.

문제: {question}

위 문제에 대해 상세한 분석과 답변을 제공해주세요."""

                analysis_text = exaone.generate(
                    prompt=prompt,
                    max_new_tokens=max_new_tokens,
                    temperature=0.7,
                    top_p=0.9,
                )

                return {
                    "success": True,
                    "question": question,
                    "analysis": analysis_text,
                    "context_used": context is not None,
                }
            except Exception as e:
                logger.error(f"[Exam 중앙 MCP 서버] EXAONE 분석 오류: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                }

        # 원본 함수를 _tools에 저장 (직접 호출용)
        self._tools["exaone_generate_text"] = _exaone_generate_text_fn
        self._tools["exaone_analyze_exam_question"] = _exaone_analyze_exam_question_fn

        # FastMCP 툴로도 등록 (MCP 클라이언트용)
        self.mcp.tool(name="exaone_generate_text")(_exaone_generate_text_fn)
        self.mcp.tool(name="exaone_analyze_exam_question")(_exaone_analyze_exam_question_fn)

        logger.info("[Exam 중앙 MCP 서버] EXAONE 툴 설정 완료")

    def _setup_integrated_tools(self) -> None:
        """KoELECTRA와 EXAONE을 연결하는 통합 FastMCP 툴을 설정합니다."""

        def _koelectra_to_exaone_pipeline_fn(
            text: str,
            use_gateway: bool = True,
            use_intent: bool = True,
            generate_response: bool = True
        ) -> dict:
            """KoELECTRA로 분류 후 EXAONE으로 응답 생성하는 통합 파이프라인."""
            try:
                result = {
                    "success": True,
                    "input_text": text,
                    "koelectra_results": {},
                    "exaone_result": None,
                }

                # 1단계: KoELECTRA 게이트웨이 분류
                if use_gateway:
                    gateway_result = self._tools["classify_gateway"](text)
                    result["koelectra_results"]["gateway"] = gateway_result
                    logger.info(f"[Exam 중앙 MCP 서버 Pipeline] 게이트웨이 분류: {gateway_result.get('gateway')}")

                # 2단계: KoELECTRA 의도 분류
                if use_intent:
                    intent_result = self._tools["classify_intent"](text)
                    result["koelectra_results"]["intent"] = intent_result
                    logger.info(f"[Exam 중앙 MCP 서버 Pipeline] 의도 분류: {intent_result.get('intent')}")

                # 3단계: EXAONE으로 응답 생성 (POLICY_BASED 또는 ADVICE인 경우)
                if generate_response:
                    gateway = result["koelectra_results"].get("gateway", {}).get("gateway", "")
                    intent = result["koelectra_results"].get("intent", {}).get("intent", "")

                    if gateway == "POLICY_BASED" or intent == "ADVICE":
                        prompt = f"""다음 시험 관련 질문에 대해 전문적이고 도움이 되는 답변을 제공해주세요.

질문: {text}

게이트웨이 분류: {gateway}
의도 분류: {intent}

위 정보를 바탕으로 질문자에게 도움이 되는 답변을 작성해주세요."""

                        exaone_result = self._tools["exaone_generate_text"](
                            prompt=prompt,
                            max_new_tokens=512,
                            temperature=0.7,
                            top_p=0.9,
                        )

                        result["exaone_result"] = exaone_result
                        logger.info("[Exam 중앙 MCP 서버 Pipeline] EXAONE 응답 생성 완료")
                    else:
                        result["exaone_result"] = {
                            "success": False,
                            "reason": f"EXAONE 호출 불필요 (gateway={gateway}, intent={intent})",
                        }

                return result
            except Exception as e:
                logger.error(f"[Exam 중앙 MCP 서버 Pipeline] 파이프라인 오류: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                }

        # 원본 함수를 _tools에 저장 (직접 호출용)
        self._tools["koelectra_to_exaone_pipeline"] = _koelectra_to_exaone_pipeline_fn

        # FastMCP 툴로도 등록 (MCP 클라이언트용)
        self.mcp.tool(name="koelectra_to_exaone_pipeline")(_koelectra_to_exaone_pipeline_fn)

        logger.info("[Exam 중앙 MCP 서버] 통합 툴 설정 완료 (KoELECTRA + EXAONE)")

    def get_mcp_server(self) -> FastMCP:
        """MCP 서버 인스턴스를 반환합니다."""
        return self.mcp

    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """툴을 호출합니다 (클라이언트용)."""
        if tool_name not in self._tools:
            return {
                "success": False,
                "error": f"툴을 찾을 수 없습니다: {tool_name}"
            }

        try:
            tool_func = self._tools[tool_name]
            # async 함수인지 확인
            import inspect
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(**kwargs)
            else:
                result = tool_func(**kwargs)
            return result
        except Exception as e:
            logger.error(f"[Exam 중앙 MCP 서버] 툴 호출 실패: {tool_name}, {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# ============================================================================
# 전역 싱글톤 인스턴스
# ============================================================================

_exam_central_mcp_server: Optional[ExamCentralMCPServer] = None


def get_central_mcp_server() -> Optional[ExamCentralMCPServer]:
    """Exam 도메인 중앙 MCP 서버 싱글톤 인스턴스를 반환합니다."""
    global _exam_central_mcp_server

    if not _FASTMCP_AVAILABLE:
        logger.warning("[Exam 중앙 MCP 서버] FastMCP가 설치되지 않아 MCP 서버를 생성할 수 없습니다.")
        return None

    if _exam_central_mcp_server is None:
        _exam_central_mcp_server = ExamCentralMCPServer()
    return _exam_central_mcp_server


# ============================================================================
# 헬퍼 함수: 중앙 MCP 서버 툴 직접 호출 (하위 호환성)
# ============================================================================

def call_koelectra_gateway_classifier(text: str) -> dict:
    """중앙 MCP 서버의 게이트웨이 분류기 툴을 호출합니다."""
    central_mcp = get_central_mcp_server()
    if central_mcp is None:
        return {
            "predicted_label": 1,
            "gateway": "POLICY_BASED",
            "confidence": 0.5,
            "probabilities": [0.33, 0.34, 0.33],
            "method": "unavailable",
        }
    return central_mcp._tools["classify_gateway"](text)


def call_koelectra_intent_classifier(text: str) -> dict:
    """중앙 MCP 서버의 의도 분류기 툴을 호출합니다."""
    central_mcp = get_central_mcp_server()
    if central_mcp is None:
        return {
            "predicted_label": 0,
            "intent": "DB_QUERY",
            "confidence": 0.5,
            "probabilities": [0.25, 0.25, 0.25, 0.25],
            "method": "unavailable",
        }
    return central_mcp._tools["classify_intent"](text)


def call_koelectra_spam_filter(text: str) -> dict:
    """중앙 MCP 서버의 스팸 필터 툴을 호출합니다."""
    central_mcp = get_central_mcp_server()
    if central_mcp is None:
        return {
            "spam_prob": 0.5,
            "label": "uncertain",
            "confidence": "low",
            "method": "unavailable",
            "threshold_zone": "ambiguous",
        }
    return central_mcp._tools["filter_spam"](text)


def call_exaone_generate_text(
    prompt: str,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 50
) -> dict:
    """중앙 MCP 서버의 EXAONE 텍스트 생성 툴을 호출합니다."""
    central_mcp = get_central_mcp_server()
    if central_mcp is None:
        return {
            "success": False,
            "error": "중앙 MCP 서버가 초기화되지 않았습니다.",
            "text": "",
        }
    return central_mcp._tools["exaone_generate_text"](
        prompt=prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k
    )


def call_exaone_analyze_exam_question(
    question: str,
    context: Optional[str] = None,
    max_new_tokens: int = 512
) -> dict:
    """중앙 MCP 서버의 EXAONE 시험 문제 분석 툴을 호출합니다."""
    central_mcp = get_central_mcp_server()
    if central_mcp is None:
        return {
            "success": False,
            "error": "중앙 MCP 서버가 초기화되지 않았습니다.",
        }
    return central_mcp._tools["exaone_analyze_exam_question"](
        question=question,
        context=context,
        max_new_tokens=max_new_tokens
    )
