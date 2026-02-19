# 스타형 MCP 시스템 구조 문서

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [파일 구조](#파일-구조)
3. [핵심 컴포넌트](#핵심-컴포넌트)
4. [정책 기반 아키텍처](#정책-기반-아키텍처)
5. [데이터 흐름](#데이터-흐름)
6. [주요 변경사항](#주요-변경사항)

---

## 시스템 개요

### 스타형 MCP (Model Context Protocol) 구조

**정책 기반 AI 에이전트 시스템**으로, 중앙 허브(EXAONE)가 맥락을 분석하여 최적의 브랜치 에이전트를 동적으로 선택합니다.

### 핵심 특징

- **정책 기반 결정**: AI 모델이 맥락(Context)을 분석하여 노드 선택
- **동적 라우팅**: 규칙은 참고용, 최종 결정은 AI 정책에 맡김
- **LangGraph 기반**: 정책 기반으로 매 노드마다 경로 분기
- **스타형 구조**: 중앙 허브(EXAONE) + 5개 브랜치 에이전트

---

## 파일 구조

```
backend/
├── main.py                          # FastAPI 애플리케이션 진입점
├── config.py                        # 설정 관리
├── dependencies.py                  # 의존성 주입 (DB, LLM 등)
├── models.py                        # 데이터베이스 모델
├── graph.py                         # 기존 LangGraph (채팅용)
│
├── controller/                      # 컨트롤러 레이어
│   └── mcp_controller.py           # MCP Gateway 컨트롤러 (Orchestrator 패턴)
│
├── routers/                         # FastAPI 라우터
│   ├── mcp_router.py               # MCP Gateway API 엔드포인트
│   ├── chat.py                     # 채팅 API
│   └── health.py                   # 헬스 체크
│
├── repository/                      # Repository 패턴
│   └── agent_repository.py         # 브랜치 에이전트 Repository
│
└── services/                        # 비즈니스 로직 레이어
    │
    ├── orchestrator/                # 🎯 오케스트레이터 (핵심)
    │   ├── mcp_orchestrator.py     # MCP 오케스트레이터 (LangGraph 실행)
    │   ├── star_mcp_graph.py       # ⭐ LangGraph 기반 스타형 그래프
    │   └── policy_based_router.py  # 🤖 정책 기반 라우터 (AI 결정)
    │
    ├── mcp_hub/                     # MCP Hub (온톨로지/정책 관리)
    │   ├── ontology.py             # 온톨로지 관리자 (규칙 정의)
    │   ├── gateway_strategy.py     # 게이트웨이 전략 (규칙+LLM 하이브리드)
    │   └── README.md               # MCP Hub 문서
    │
    ├── star_hub/                    # 스타 허브 (중앙 허브)
    │   └── exaone_hub.py           # EXAONE 중앙 허브 (유문작업)
    │
    ├── branch_agents/                # 브랜치 에이전트 (5개)
    │   ├── base_adapter.py         # 기본 어댑터 인터페이스
    │   ├── spam_filter_adapter.py  # 스팸 필터 어댑터
    │   ├── sentiment_adapter.py    # 감정 분석 어댑터
    │   ├── summary_adapter.py      # 요약 어댑터
    │   ├── classification_adapter.py # 분류 어댑터
    │   └── notification_adapter.py  # 알림 어댑터
    │
    ├── mcp_gateway/                 # MCP Gateway (KoELECTRA 필터)
    │   ├── graph_v2.py             # KoELECTRA 게이트웨이 그래프
    │   └── README.md               # Gateway 문서
    │
    ├── verdict_agent/               # 판별기 에이전트 (레거시)
    │   ├── base_model.py           # 요청/응답 모델
    │   └── state_model.py          # 상태 관리 모델
    │
    ├── text_classifier/             # 텍스트 분류기 (koELECTRA 학습)
    │   ├── train.py                # 학습 스크립트
    │   └── lora_adapter.py         # LoRA 학습 스크립트
    │
    ├── spam_agent/                  # 스팸 에이전트 (EXAONE 학습)
    │   ├── lora_adapter.py         # LoRA 학습 스크립트
    │   └── ...                     # 기타 학습/ETL 스크립트
    │
    └── ...                          # 기타 서비스 (chat_service, rag, database 등)
```

---

## 핵심 컴포넌트

### 1. Orchestrator (`services/orchestrator/`)

#### `star_mcp_graph.py` ⭐
**LangGraph 기반 스타형 그래프 구조**

- **역할**: 정책 기반으로 매 노드마다 경로 분기
- **노드 구성**:
  - `gateway`: **KoELECTRA를 1차 필터로 사용하는 게이트웨이**
    - KoELECTRA로 빠른 스팸 확률 계산
    - 명확한 경우: 즉시 결정 (deny/allow)
    - 애매한 경우: EXAONE LLM으로 정책 결정
  - `branch_router`: 브랜치 선택
  - `spam_filter`, `sentiment`, `summary`, `classification`, `notification`: 브랜치 노드
  - `exaone_hub`: 중앙 허브 (유문작업)
- **정책 분기 함수**:
  - `route_after_gateway()`: Gateway → deny/allow/route 분기
  - `route_after_branch_router()`: Branch Router → 브랜치 선택
  - `route_after_branch()`: 브랜치 → EXAONE 허브

**Gateway 전략**:
1. **KoELECTRA 1차 필터**: 빠른 스팸 확률 계산
2. **명확한 경우** (spam_prob < 0.3 또는 > 0.8): 즉시 결정
3. **애매한 경우** (0.3 <= spam_prob <= 0.8): EXAONE LLM 정책 결정

#### `policy_based_router.py` 🤖
**정책 기반 라우터 (AI 결정)**

- **역할**: AI 모델이 맥락을 분석하여 최적의 노드 선택
- **사용 모델**: **EXAONE LLM**
- **호출 조건**: Gateway 노드에서 KoELECTRA 결과가 애매한 경우만 호출
- **특징**:
  - 규칙은 참고용으로만 사용
  - KoELECTRA 결과를 맥락에 포함
  - EXAONE LLM이 최종 결정
  - 동적 선택 (Context-aware)
  - 여러 브랜치 선택 가능

**참고**:
- **Gateway 노드**: KoELECTRA 1차 필터 + EXAONE LLM (애매한 경우)
- **Spam Filter 브랜치**: KoELECTRA 사용 (스팸 확률 계산)

#### `mcp_orchestrator.py`
**MCP 오케스트레이터**

- **역할**: LangGraph 실행 및 파이프라인 조율
- **메서드**:
  - `process_request()`: LangGraph 실행

### 2. MCP Hub (`services/mcp_hub/`)

#### `ontology.py`
**온톨로지 관리자**

- **역할**: 규칙 정의 및 평가 (참고용)
- **구성**:
  - `OntologyRule`: 규칙 정의 (우선순위, 조건, 액션)
  - `RoutingPolicy`: 라우팅 정책
  - `OntologyManager`: 규칙 평가 및 제안

#### `gateway_strategy.py`
**게이트웨이 전략 (하이브리드)**

- **역할**: 규칙 기반 우선 + LLM 보조
- **전략**:
  1. 규칙 기반 게이트 (1차 필터)
  2. KoELECTRA 필터 (2차 필터)
  3. LLM 보조 게이트 (예외 처리)

### 3. Star Hub (`services/star_hub/`)

#### `exaone_hub.py`
**EXAONE 중앙 허브**

- **역할**: 유문작업 (글 다듬어서 출력)
- **입력**: 원본 텍스트 + 브랜치 에이전트 결과
- **출력**: 다듬어진 최종 텍스트

### 4. Branch Agents (`services/branch_agents/`)

#### 어댑터 구조
- **BaseAdapter**: 기본 인터페이스
- **5개 브랜치 어댑터**:
  - `SpamFilterAdapter`: **KoELECTRA 사용** (스팸 필터링)
  - `SentimentAdapter`: 감정 분석 (스텁)
  - `SummaryAdapter`: 요약 (스텁)
  - `ClassificationAdapter`: 분류 (스텁)
  - `NotificationAdapter`: 알림 (스텁)

**중요**:
- **Gateway 노드**: **KoELECTRA 1차 필터** + EXAONE LLM (애매한 경우만)
- **Spam Filter 브랜치**: KoELECTRA 사용 (스팸 확률 계산)

### 5. Repository (`repository/`)

#### `agent_repository.py`
**에이전트 Repository**

- **역할**: 브랜치 에이전트 관리 및 실행
- **메서드**:
  - `get_adapter()`: 브랜치 어댑터 반환
  - `execute_branch()`: 브랜치 실행
  - `list_branches()`: 사용 가능한 브랜치 목록

### 6. Controller (`controller/`)

#### `mcp_controller.py`
**MCP Controller**

- **역할**: HTTP 요청/응답 처리, 세션 상태 관리
- **메서드**:
  - `process_gateway_request()`: Orchestrator 호출
  - `get_session_history()`: 세션 히스토리 조회
  - `clear_session()`: 세션 삭제

---

## 정책 기반 아키텍처

### 정책 기반 vs 규칙 기반

| 구분 | 규칙 기반 (이전) | 정책 기반 (개선 후) |
|------|------------------|-------------------|
| **결정 주체** | 정규식 매칭 | AI 모델 (EXAONE) |
| **분기 방식** | 조건 일치 → 고정 경로 | 맥락 분석 → 최적 노드 선택 |
| **규칙 역할** | 결정적 역할 | 참고용 |
| **유연성** | 낮음 (고정 규칙) | 높음 (동적 선택) |
| **맥락 인식** | 없음 | 있음 (Context-aware) |

### 정책 기반 결정 흐름

```
1. Gateway 노드
   ↓
   KoELECTRA 1차 필터 실행
   ↓
   spam_prob 계산
   ↓
   분기:
   ├─ spam_prob < 0.3 → 즉시 allow (EXAONE LLM 호출 안 함)
   ├─ spam_prob > 0.8 → 즉시 deny (EXAONE LLM 호출 안 함)
   └─ 0.3 <= spam_prob <= 0.8 → EXAONE LLM 정책 결정
       ↓
       PolicyBasedRouter.get_routing_decision()
       ↓
       - 규칙 제안 수집 (참고용, OntologyManager)
       - KoELECTRA 결과 포함 (맥락 정보)
       - 맥락 정보 수집 (세션, 사용자 정보 등)
       - EXAONE LLM 호출 (정책 결정)
       ↓
       EXAONE LLM이 맥락 분석하여 결정:
       - action: deny/allow/route
       - target_branch: 최적의 브랜치 선택
       - confidence: 신뢰도
   ↓
2. 정책 기반 분기
   - deny → END
   - allow → exaone_hub
   - route → branch_router
   ↓
3. Branch Router 노드
   ↓
   target_branch에 따라 브랜치 선택
   ↓
4. 브랜치 노드 실행
   - spam_filter → KoELECTRA 사용 (스팸 확률 계산)
   - 다른 브랜치 → 각각의 로직 실행
   ↓
5. EXAONE 허브 (유문작업)
```

**모델 사용 위치**:
- **Gateway 노드**: **KoELECTRA 1차 필터** + EXAONE LLM (애매한 경우만)
- **Spam Filter 브랜치**: KoELECTRA (스팸 필터링)
- **EXAONE 허브**: EXAONE LLM (유문작업)

### 정책 결정 예시

```python
# PolicyBasedRouter가 AI 모델에게 요청
decision = await router.get_routing_decision(
    text="불만이 많아서 화가 납니다. 이 서비스는 최악입니다.",
    context={
        "session_id": "session_123",
        "user_id": "user_456",
        "previous_requests": [...]
    }
)

# AI 모델 응답 (JSON)
{
    "action": "route",
    "target_branch": "sentiment",  # 감정 분석 필요
    "reason": "부정적 감정이 강하게 표현되어 감정 분석이 필요합니다.",
    "confidence": 0.95,
    "additional_branches": ["spam_filter"]  # 스팸 필터도 함께 실행
}
```

---

## 데이터 흐름

### 전체 파이프라인

```
[FastAPI Router]
    ↓
[Controller]
    ↓
[Orchestrator]
    ↓
[LangGraph 실행]
    ↓
[Gateway 노드]
    ↓ (정책 기반 분기)
    ├─ deny → END
    ├─ allow → [EXAONE Hub] → END
    └─ route → [Branch Router]
                ↓ (정책 기반 분기)
                ├─ spam_filter → [Spam Filter] → [EXAONE Hub] → END
                ├─ sentiment → [Sentiment] → [EXAONE Hub] → END
                ├─ summary → [Summary] → [EXAONE Hub] → END
                ├─ classification → [Classification] → [EXAONE Hub] → END
                └─ notification → [Notification] → [EXAONE Hub] → END
```

### 상세 흐름

1. **HTTP 요청 수신** (`mcp_router.py`)
   - `/api/mcp/gateway` 엔드포인트
   - `GatewayRequest` 모델로 파싱

2. **Controller 처리** (`mcp_controller.py`)
   - 세션 ID 생성
   - Orchestrator 호출

3. **Orchestrator 실행** (`mcp_orchestrator.py`)
   - LangGraph 실행 (`star_mcp_graph.py`)

4. **Gateway 노드** (`star_mcp_graph.py`)
   - **KoELECTRA 1차 필터**: 빠른 스팸 확률 계산
   - 명확한 경우 (spam_prob < 0.3 또는 > 0.8): 즉시 결정
   - 애매한 경우 (0.3 <= spam_prob <= 0.8): `PolicyBasedRouter` 호출
   - **EXAONE LLM**이 맥락 분석하여 정책 결정

5. **정책 기반 분기**
   - `route_after_gateway()` 함수로 분기

6. **브랜치 노드 실행**
   - `AgentRepository`를 통해 브랜치 어댑터 실행

7. **EXAONE 허브** (`exaone_hub.py`)
   - 브랜치 결과를 받아 유문작업 수행

8. **응답 반환**
   - `GatewayResponse` 모델로 반환

---

## 주요 변경사항

### 1. 정책 기반 구조 도입

**이전**: 규칙 기반 (정규식 매칭)
```python
# ontology.py에서 규칙 매칭
if re.search(rule.condition, text):
    return rule.action
```

**개선 후**: 정책 기반 (AI 결정)
```python
# policy_based_router.py에서 AI 결정
decision = await router.get_routing_decision(
    text=text,
    context=context  # 맥락 정보 포함
)
```

### 2. LangGraph 기반 그래프 구조

**이전**: if-else 기반 분기
```python
if action == "deny":
    return deny_result
elif action == "allow":
    return allow_result
```

**개선 후**: LangGraph conditional edges
```python
graph.add_conditional_edges(
    "gateway",
    route_after_gateway,  # 정책 기반 분기 함수
    {
        "end": END,
        "exaone_hub": "exaone_hub",
        "branch_router": "branch_router",
    }
)
```

### 3. 파일 구조 개선

**새로 추가된 파일**:
- `services/orchestrator/star_mcp_graph.py`: LangGraph 그래프 정의
- `services/orchestrator/policy_based_router.py`: 정책 기반 라우터

**수정된 파일**:
- `services/orchestrator/mcp_orchestrator.py`: LangGraph 실행으로 변경
- `services/orchestrator/star_mcp_graph.py`: Gateway 노드에서 PolicyBasedRouter 사용

---

## 핵심 설계 원칙

### 1. 정책 기반 결정
- AI 모델이 맥락을 분석하여 최적의 노드 선택
- 규칙은 참고용으로만 사용
- 동적 선택 (Context-aware)

### 2. 스타형 구조
- 중앙 허브 (EXAONE): 유문작업만 수행
- 브랜치 에이전트: 각각 특화된 작업 수행
- 독립성: 브랜치들은 서로 독립적

### 3. Repository 패턴
- 브랜치 에이전트 관리 추상화
- 어댑터 패턴으로 확장성 확보

### 4. Orchestrator 패턴
- 전체 파이프라인 조율
- 관심사 분리

---

## 확장 방법

### 새로운 브랜치 에이전트 추가

1. **어댑터 생성** (`services/branch_agents/new_adapter.py`)
```python
from backend.services.branch_agents.base_adapter import BaseAdapter

class NewAdapter(BaseAdapter):
    async def execute(self, text: str, metadata=None):
        # 구현
        return AgentResult(...)
```

2. **온톨로지에 브랜치 추가** (`services/mcp_hub/ontology.py`)
```python
class AgentBranch(str, Enum):
    NEW_BRANCH = "new_branch"
```

3. **Repository에 등록** (`repository/agent_repository.py`)
```python
self._adapters[AgentBranch.NEW_BRANCH] = NewAdapter()
```

4. **그래프에 노드 추가** (`services/orchestrator/star_mcp_graph.py`)
```python
graph.add_node("new_branch", new_branch_node)
graph.add_conditional_edges(
    "branch_router",
    route_after_branch_router,
    {
        "new_branch": "new_branch",
        ...
    }
)
```

---

## 테스트

### 테스트 파일

- `test_mcp_components.py`: 컴포넌트 단위 테스트
- `test_star_mcp_simple.py`: 간단한 통합 테스트
- `test_star_mcp.py`: 전체 파이프라인 테스트

### 실행 방법

```bash
# 컴포넌트 테스트
python backend/test_mcp_components.py

# FastAPI 서버 실행
python -m uvicorn backend.main:app --reload

# API 테스트
curl -X POST http://localhost:8000/api/mcp/gateway \
  -H "Content-Type: application/json" \
  -d '{"text": "테스트 메시지"}'
```

---

## 문서

- `ARCHITECTURE.md`: 전체 아키텍처 설명
- `SYSTEM_STRUCTURE.md`: 이 문서 (파일 구조)
- `services/mcp_hub/README.md`: MCP Hub 문서
- `services/mcp_gateway/README.md`: Gateway 문서

---

## 요약

이 시스템은 **정책 기반 스타형 MCP 구조**로, AI 모델이 맥락을 분석하여 최적의 브랜치 에이전트를 동적으로 선택합니다. LangGraph를 사용하여 정책 기반으로 매 노드마다 경로가 분기되며, 규칙은 참고용으로만 사용됩니다.

**핵심**: 연결 방식(Topology)은 규칙으로 규격화되어 있지만, 노드 선택 결정은 AI 정책에 맡기는 구조입니다.

