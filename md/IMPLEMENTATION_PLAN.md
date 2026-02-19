# 시험 질문 의도 분류 시스템 구현 계획

## 🎯 목표

`spam_prob` 기반 분기를 **의도(Intent) 및 복잡도(Complexity)** 기반으로 전환하여, 시험 문제 관련성과 처리 복잡도를 정확히 판단하는 시스템 구축.

## 📋 구현 단계

### Phase 1: 스키마 및 모델 정의 (1-2일)

#### 1.1 새로운 스키마 정의

**파일**: `backend/domain/admin/agents/analysis/intent_classifier.py` (신규 생성)

```python
from typing import Literal, TypedDict, Optional, List

class ExamIntent(TypedDict):
    """시험 질문 의도 분류 결과"""
    intent: Literal["DB_QUERY", "EXPLAIN", "ADVICE", "OUT_OF_DOMAIN"]
    confidence: float  # 0.0 ~ 1.0
    is_complex: bool  # 복합적인 질문인지 여부
    entities_found: List[str]  # 추출된 엔티티 목록
    missing_entities: List[str]  # 누락된 필수 엔티티

class ExamEntities(TypedDict):
    """추출된 시험 관련 엔티티"""
    year: Optional[int]
    exam_type: Optional[str]  # "국가직" | "지방직"
    job_series: Optional[str]
    grade: Optional[str]
    subject: Optional[str]
    question_no: Optional[int]
    has_all_required: bool  # 필수 엔티티 모두 있는지
```

#### 1.2 엔티티 추출 모듈 생성

**파일**: `backend/domain/admin/agents/analysis/entity_extractor.py` (신규 생성)

기존 파싱 함수들을 모듈화하고 개선:
- `_resolve_relative_year()` → `extract_year()`
- `_parse_exam_type()` → `extract_exam_type()`
- `_parse_subject()` → `extract_subject()`
- `_parse_question_no()` → `extract_question_no()`
- `_parse_job_series()` → `extract_job_series()`
- `_parse_grade()` → `extract_grade()`

**통합 함수**:
```python
def extract_all_entities(text: str, conn: psycopg.Connection) -> ExamEntities:
    """모든 엔티티를 한 번에 추출"""
    ...
```

---

### Phase 2: 의도 분류기 구현 (2-3일)

#### 2.1 규칙 기반 의도 분류 (1차 구현)

**파일**: `backend/domain/admin/agents/analysis/intent_classifier.py`

```python
def classify_intent_rule_based(text: str, entities: ExamEntities) -> ExamIntent:
    """규칙 기반 의도 분류 (빠른 판단)"""

    # 1. OUT_OF_DOMAIN 체크
    out_of_domain_keywords = ["날씨", "음식", "배고파", "놀고싶어"]
    if any(kw in text for kw in out_of_domain_keywords):
        return {
            "intent": "OUT_OF_DOMAIN",
            "confidence": 0.9,
            "is_complex": False,
            "entities_found": [],
            "missing_entities": []
        }

    # 2. DB_QUERY 체크 (명확한 엔티티 존재)
    if entities["has_all_required"]:
        return {
            "intent": "DB_QUERY",
            "confidence": 0.9,
            "is_complex": False,
            "entities_found": [k for k, v in entities.items() if v is not None],
            "missing_entities": []
        }

    # 3. EXPLAIN 체크 (해설 관련 키워드)
    explain_keywords = ["왜", "이유", "설명", "해설", "원리", "근거", "판례"]
    if any(kw in text for kw in explain_keywords):
        return {
            "intent": "EXPLAIN",
            "confidence": 0.7,
            "is_complex": True,
            "entities_found": [k for k, v in entities.items() if v is not None],
            "missing_entities": [k for k, v in entities.items() if v is None and k != "has_all_required"]
        }

    # 4. ADVICE 체크 (학습 상담 키워드)
    advice_keywords = ["어떻게", "방법", "공부", "학습", "합격", "가능", "추천"]
    if any(kw in text for kw in advice_keywords):
        return {
            "intent": "ADVICE",
            "confidence": 0.7,
            "is_complex": True,
            "entities_found": [],
            "missing_entities": []
        }

    # 5. 기본값: DB_QUERY (엔티티 일부만 있으면)
    if any([entities["year"], entities["subject"], entities["question_no"]]):
        return {
            "intent": "DB_QUERY",
            "confidence": 0.5,
            "is_complex": False,
            "entities_found": [k for k, v in entities.items() if v is not None],
            "missing_entities": [k for k, v in entities.items() if v is None and k != "has_all_required"]
        }

    # 6. 애매한 경우
    return {
        "intent": "DB_QUERY",  # 기본값
        "confidence": 0.3,
        "is_complex": True,
        "entities_found": [],
        "missing_entities": ["year", "subject", "question_no"]
    }
```

#### 2.2 KoELECTRA 기반 의도 분류 (2차 구현, 선택적)

**향후 개선**: KoELECTRA 모델을 재학습하여 의도 분류 전용 모델로 사용
- 현재는 규칙 기반으로 시작
- 모델 재학습 후 교체 가능하도록 인터페이스 설계

---

### Phase 3: ExamFlow 개편 (2일)

#### 3.1 새로운 ExamFlow 구현

**파일**: `backend/domain/admin/orchestrators/exam_flow_v2.py` (신규 생성)

```python
from backend.domain.admin.agents.analysis.intent_classifier import classify_intent_rule_based
from backend.domain.admin.agents.analysis.entity_extractor import extract_all_entities
from backend.domain.admin.services.exam_service import ExamService
from backend.domain.admin.agents.exam_agent import ExamAgent

class ExamFlowV2:
    """Exam 요청 처리 Orchestrator V2 (의도 기반)"""

    def __init__(self):
        self._exam_service = ExamService()
        self._exam_agent = ExamAgent()

    async def process_exam_request(
        self, request_text: str, request_data: dict
    ) -> dict:
        """의도 기반 요청 처리"""

        # 1단계: 엔티티 추출
        conn = get_db_connection()
        entities = extract_all_entities(request_text, conn)

        # 2단계: 의도 분류
        intent_result = classify_intent_rule_based(request_text, entities)

        print(
            f"[ExamFlowV2] 의도: {intent_result['intent']}, "
            f"신뢰도: {intent_result['confidence']:.2f}, "
            f"복잡도: {intent_result['is_complex']}",
            flush=True
        )

        # 3단계: 의도별 분기
        if intent_result["intent"] == "DB_QUERY":
            return await self._handle_db_query(request_data, entities, intent_result)
        elif intent_result["intent"] == "EXPLAIN":
            return await self._handle_explain(request_text, request_data, entities, intent_result)
        elif intent_result["intent"] == "ADVICE":
            return await self._handle_advice(request_text, request_data, intent_result)
        else:  # OUT_OF_DOMAIN
            return await self._handle_out_of_domain(request_text, intent_result)

    async def _handle_db_query(self, request_data: dict, entities: ExamEntities, intent_result: ExamIntent) -> dict:
        """DB 조회 요청 처리"""

        # 필수 엔티티 확인
        if not entities["has_all_required"]:
            missing = intent_result["missing_entities"]
            return {
                "success": False,
                "method": "rule_based",
                "intent": "DB_QUERY",
                "error": f"필수 정보가 누락되었습니다: {', '.join(missing)}",
                "missing_entities": missing,
                "suggestion": self._generate_clarification_message(missing)
            }

        # 규칙 기반 서비스로 처리
        return await self._exam_service.handle_request(request_data, {"intent": intent_result})

    async def _handle_explain(self, request_text: str, request_data: dict, entities: ExamEntities, intent_result: ExamIntent) -> dict:
        """해설 요청 처리 (LLM 필요)"""

        # 정책 기반 에이전트로 처리
        return await self._exam_agent.handle_request(
            request_text,
            request_data,
            {"intent": intent_result, "entities": entities}
        )

    async def _handle_advice(self, request_text: str, request_data: dict, intent_result: ExamIntent) -> dict:
        """학습 상담 요청 처리 (LLM 필요)"""

        # 정책 기반 에이전트로 처리
        return await self._exam_agent.handle_request(
            request_text,
            request_data,
            {"intent": intent_result}
        )

    async def _handle_out_of_domain(self, request_text: str, intent_result: ExamIntent) -> dict:
        """도메인 외 요청 처리"""

        return {
            "success": False,
            "method": "out_of_domain",
            "intent": "OUT_OF_DOMAIN",
            "error": "공무원 시험 및 학습 관련 질문에만 답변을 드릴 수 있습니다.",
            "user_message": "공무원 시험 관련 질문을 해주시면 도와드리겠습니다. 예: '작년 회계학 3번 정답 뭐야?'"
        }

    def _generate_clarification_message(self, missing: List[str]) -> str:
        """누락된 정보 요청 메시지 생성"""
        messages = {
            "year": "연도를 알려주세요. (예: 2024년, 작년)",
            "subject": "과목명을 알려주세요. (예: 회계학, 행정법총론)",
            "question_no": "문항 번호를 알려주세요. (예: 3번)",
            "exam_type": "시험 구분을 알려주세요. (예: 국가직, 지방직)",
            "job_series": "직렬을 알려주세요. (예: 교육행정직, 일반행정직)"
        }
        return "다음 정보를 추가로 알려주세요:\n" + "\n".join(f"- {messages.get(k, k)}" for k in missing)
```

---

### Phase 4: 기존 코드와 통합 (1-2일)

#### 4.1 Feature Flag 추가

**파일**: `backend/config.py`

```python
# 의도 기반 분기 사용 여부 (기본값: False)
USE_INTENT_BASED_ROUTING = os.getenv("USE_INTENT_BASED_ROUTING", "false").lower() in ("true", "1", "yes")
```

#### 4.2 ExamFlow 선택적 사용

**파일**: `backend/domain/admin/orchestrators/exam_flow.py`

```python
from backend.config import settings

class ExamFlow:
    """Exam 요청 처리 Orchestrator (레거시 호환)"""

    def __init__(self):
        if settings.USE_INTENT_BASED_ROUTING:
            from backend.domain.admin.orchestrators.exam_flow_v2 import ExamFlowV2
            self._flow_v2 = ExamFlowV2()
        else:
            self._exam_service = ExamService()
            self._exam_agent = ExamAgent()

    async def process_exam_request(self, request_text: str, request_data: dict) -> dict:
        if settings.USE_INTENT_BASED_ROUTING:
            return await self._flow_v2.process_exam_request(request_text, request_data)
        else:
            # 기존 로직 (spam_prob 기반)
            ...
```

---

### Phase 5: 테스트 및 검증 (2-3일)

#### 5.1 테스트 케이스 작성

**파일**: `backend/tests/test_intent_classifier.py` (신규 생성)

```python
def test_db_query_intent():
    """명확한 DB 조회 요청 테스트"""
    text = "2024년 지방직 9급 교육행정직 회계학 3번 정답 뭐야?"
    entities = extract_all_entities(text, conn)
    intent = classify_intent_rule_based(text, entities)

    assert intent["intent"] == "DB_QUERY"
    assert intent["confidence"] > 0.8
    assert not intent["is_complex"]

def test_explain_intent():
    """해설 요청 테스트"""
    text = "신뢰보호의 원칙이 이 판례에서 왜 적용 안 돼?"
    entities = extract_all_entities(text, conn)
    intent = classify_intent_rule_based(text, entities)

    assert intent["intent"] == "EXPLAIN"
    assert intent["is_complex"] == True

def test_advice_intent():
    """학습 상담 요청 테스트"""
    text = "직장인인데 하루 4시간 공부로 합격 가능할까?"
    entities = extract_all_entities(text, conn)
    intent = classify_intent_rule_based(text, entities)

    assert intent["intent"] == "ADVICE"
    assert intent["is_complex"] == True

def test_out_of_domain():
    """도메인 외 요청 테스트"""
    text = "오늘 날씨 어때?"
    entities = extract_all_entities(text, conn)
    intent = classify_intent_rule_based(text, entities)

    assert intent["intent"] == "OUT_OF_DOMAIN"
```

#### 5.2 통합 테스트

- 실제 API 엔드포인트 테스트
- 성능 비교 (기존 vs 신규)
- 정확도 측정

---

### Phase 6: 모니터링 및 로깅 개선 (1일)

#### 6.1 로깅 강화

```python
logger.info(f"[ExamFlowV2] 요청 분석 완료", extra={
    "intent": intent_result["intent"],
    "confidence": intent_result["confidence"],
    "entities_found": intent_result["entities_found"],
    "missing_entities": intent_result["missing_entities"],
    "processing_time_ms": processing_time
})
```

#### 6.2 메트릭 수집

- 의도별 분포
- 처리 시간 비교
- 정확도 추적

---

## 📁 파일 구조

```
backend/
├── domain/admin/
│   ├── agents/analysis/
│   │   ├── intent_classifier.py      # 신규: 의도 분류기
│   │   ├── entity_extractor.py      # 신규: 엔티티 추출 모듈
│   │   └── spam_detector.py         # 기존: 유지 (레거시 호환)
│   │
│   └── orchestrators/
│       ├── exam_flow.py             # 수정: Feature flag 추가
│       └── exam_flow_v2.py          # 신규: 의도 기반 플로우
│
└── tests/
    └── test_intent_classifier.py    # 신규: 테스트
```

---

## 🔄 마이그레이션 전략

### 단계별 전환

1. **Phase 1-3**: 신규 시스템 구축 (기존 시스템과 병행)
2. **Phase 4**: Feature flag로 선택적 사용
3. **Phase 5**: 테스트 및 검증
4. **Phase 6**: 점진적 전환 (10% → 50% → 100%)
5. **Phase 7**: 레거시 코드 제거 (검증 완료 후)

### 롤백 계획

- Feature flag로 즉시 기존 시스템으로 복귀 가능
- A/B 테스트로 성능 비교 후 결정

---

## 🎯 예상 효과

1. **정확도 향상**: 의도 기반 분류로 더 정확한 라우팅
2. **비용 절감**: 불필요한 LLM 호출 감소
3. **속도 개선**: 명확한 요청은 즉시 DB 조회
4. **사용자 경험**: 누락된 정보를 명확히 안내

---

## 📝 다음 단계

1. **Phase 1 시작**: 스키마 및 엔티티 추출 모듈 구현
2. **검토**: 팀 리뷰 및 피드백 수집
3. **조정**: 계획 수정 및 우선순위 조정

