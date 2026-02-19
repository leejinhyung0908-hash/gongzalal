# 스타형 MCP 구조 아키텍처

## 🏗️ 전체 구조 개요

```
                    [FastAPI Router]
                         ↓
                    [Controller]
                    (Orchestrator Pattern)
                         ↓
                    [Orchestrator]
                    (전체 파이프라인 조율)
                         ↓
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
  [Gateway Strategy]  [Agent Repository]  [EXAONE Hub]
  (규칙기반+LLM보조)   (브랜치 관리)      (중앙 허브)
        ↓                ↓                ↓
  [Ontology Manager]  [Branch Agents]   [유문작업]
  (온톨로지/정책)      (5개 브랜치)      (글 다듬기)
        ↓
  [KoELECTRA Filter]
  (1차 필터)
```

## 📊 스타형 구조 특징

### 중앙 허브 (Star Hub)
- **EXAONE**: 중앙 허브 역할
- **역할**: 유문작업만 수행 (글 다듬어서 출력)
- **입력**: 원본 텍스트 + 브랜치 에이전트 결과
- **출력**: 다듬어진 최종 텍스트

### 브랜치 에이전트 (Branch Agents)
- **5개 브랜치**: 각각 특화된 작업 수행
  - `spam_filter`: 스팸 필터링 (KoELECTRA 사용)
  - `sentiment`: 감정 분석
  - `summary`: 요약
  - `classification`: 텍스트 분류
  - `notification`: 알림/알림

## 🔄 처리 흐름 (상세)

### 1단계: Controller (진입점)
**파일**: `backend/controller/mcp_controller.py`

```python
McpController.process_gateway_request()
  ↓
  - 입력 검증
  - 세션/요청 ID 생성
  - Orchestrator 호출
  - 결과를 GatewayResponse로 변환
  - 세션 상태 저장
```

**역할**:
- HTTP 요청/응답 처리
- 세션 상태 관리
- Orchestrator와의 인터페이스

---

### 2단계: Orchestrator (파이프라인 조율)
**파일**: `backend/services/orchestrator/mcp_orchestrator.py`

```python
McpOrchestrator.process_request()
  ↓
  1. Gateway Strategy 실행
     → 라우팅 결정 (deny/allow/route)
  ↓
  2. 액션에 따른 분기:
     - deny → 즉시 반환
     - allow → EXAONE 허브만 실행
     - route → 브랜치 에이전트 실행
  ↓
  3. EXAONE 허브 실행
     → 브랜치 결과를 받아 유문작업
  ↓
  4. 최종 결과 반환
```

**역할**:
- 전체 파이프라인 조율
- Gateway Strategy, Agent Repository, EXAONE Hub 연결
- 액션에 따른 분기 처리

---

### 3단계: Gateway Strategy (라우팅 결정)
**파일**: `backend/services/mcp_hub/gateway_strategy.py`

#### 3-1. 규칙기반 게이트 (1차 필터)
```python
OntologyManager.get_routing_decision()
  ↓
  - 온톨로지 규칙 평가 (우선순위 기반)
  - 빠른 결정 (deny/allow/route)
  - confidence=high → 즉시 반환 (80% 케이스)
```

**규칙 우선순위**:
- 100: 명확한 스팸 패턴 (즉시 차단)
- 95: URL/링크 감지 (격리)
- 80: 감정 분석 필요
- 70: 요약 필요 (긴 텍스트)
- 50: 기본 스팸 필터

#### 3-2. KoELECTRA 필터 (2차 필터)
```python
mcp_tool_koelectra_filter.invoke()
  ↓
  - spam_prob 산출
  - spam_prob < 0.3 또는 > 0.8 → 즉시 결정 (15% 케이스)
  - 0.3 <= spam_prob <= 0.8 → 다음 단계
```

#### 3-3. LLM 보조 게이트 (3차 필터, 예외 처리)
```python
_run_llm_gateway()
  ↓
  - 규칙과 KoELECTRA가 모두 모호한 경우만 호출 (5% 케이스)
  - EXAONE으로 최종 라우팅 결정
```

**결정 병합 우선순위**: LLM > KoELECTRA > 규칙

---

### 4단계: Agent Repository (브랜치 관리)
**파일**: `backend/repository/agent_repository.py`

```python
AgentRepository.execute_branch()
  ↓
  - 브랜치 타입에 맞는 어댑터 선택
  - 어댑터 실행
  - AgentResult 반환
```

**브랜치 어댑터들**:
- `SpamFilterAdapter`: KoELECTRA 사용
- `SentimentAdapter`: 감정 분석 (스텁)
- `SummaryAdapter`: 요약 (스텁)
- `ClassificationAdapter`: 분류 (스텁)
- `NotificationAdapter`: 알림 (스텁)

---

### 5단계: EXAONE Star Hub (중앙 허브)
**파일**: `backend/services/star_hub/exaone_hub.py`

```python
ExaoneHub.refine_output()
  ↓
  1. 브랜치 결과 요약
  2. EXAONE 프롬프트 구성
     - 원본 텍스트
     - 브랜치 분석 결과
     - 유문작업 요구사항
  3. EXAONE 실행
  4. 다듬어진 최종 출력 반환
```

**역할**:
- **유문작업만 수행**: 글 다듬어서 출력
- 브랜치 결과를 종합하여 일관성 있는 출력 생성
- 자연스럽고 읽기 쉬운 문장으로 다듬기

---

## 📁 디렉토리 구조

```
backend/
├── controller/
│   └── mcp_controller.py          # Controller (Orchestrator Pattern)
│
├── services/
│   ├── orchestrator/
│   │   └── mcp_orchestrator.py    # Orchestrator (파이프라인 조율)
│   │
│   ├── mcp_hub/
│   │   ├── ontology.py            # 온톨로지 관리 (규칙 정의)
│   │   └── gateway_strategy.py    # Gateway 전략 (규칙기반+LLM보조)
│   │
│   ├── star_hub/
│   │   └── exaone_hub.py          # EXAONE 중앙 허브 (유문작업)
│   │
│   ├── branch_agents/
│   │   ├── base_adapter.py        # 기본 어댑터
│   │   ├── spam_filter_adapter.py # 스팸 필터
│   │   ├── sentiment_adapter.py   # 감정 분석
│   │   ├── summary_adapter.py     # 요약
│   │   ├── classification_adapter.py # 분류
│   │   └── notification_adapter.py  # 알림
│   │
│   └── mcp_gateway/
│       └── graph_v2.py            # KoELECTRA 필터 (1차 필터)
│
└── repository/
    └── agent_repository.py        # Agent Repository (브랜치 관리)
```

---

## 🔀 데이터 흐름 예시

### 시나리오 1: 명확한 스팸 (규칙 기반 즉시 차단)

```
입력: "긴급! 계정 정보가 유출되었습니다. 지금 바로 링크를 클릭하세요!"

1. Controller → Orchestrator
2. Orchestrator → Gateway Strategy
3. Gateway Strategy → Ontology Manager
   - 규칙 우선순위 100 매칭: "긴급|당첨|보상|계정.*유출"
   - action: "deny", confidence: "high"
4. Orchestrator → 즉시 반환 (deny)
5. Controller → GatewayResponse 반환
```

**결과**: 브랜치 에이전트 실행 없음, EXAONE 허브 실행 없음

---

### 시나리오 2: 애매한 케이스 (브랜치 실행 + EXAONE 허브)

```
입력: "새로운 투자 기회를 소개합니다. 높은 수익률을 보장합니다."

1. Controller → Orchestrator
2. Orchestrator → Gateway Strategy
3. Gateway Strategy:
   - 규칙: confidence="low", action="route", target_branch="spam_filter"
   - KoELECTRA: spam_prob=0.55 (모호함)
   - LLM 보조: 최종 결정 (route → spam_filter)
4. Orchestrator → Agent Repository
   - SpamFilterAdapter 실행
   - 결과: spam_prob=0.55, label="uncertain"
5. Orchestrator → EXAONE Hub
   - 브랜치 결과 요약
   - EXAONE으로 유문작업 수행
   - 최종 출력 생성
6. Controller → GatewayResponse 반환
```

**결과**: 스팸 필터 브랜치 실행 → EXAONE 허브로 유문작업

---

### 시나리오 3: 정상 메일 (허용)

```
입력: "안녕하세요. 다음 주 회의 시간 조율 부탁드립니다."

1. Controller → Orchestrator
2. Orchestrator → Gateway Strategy
3. Gateway Strategy:
   - 규칙: confidence="low"
   - KoELECTRA: spam_prob=0.15 (명확히 낮음)
   - 결정: action="allow"
4. Orchestrator → EXAONE Hub (브랜치 없이)
   - 원본 텍스트만으로 유문작업
5. Controller → GatewayResponse 반환
```

**결과**: 브랜치 실행 없음, EXAONE 허브만 실행

---

## 🎯 핵심 설계 원칙

### 1. 스타형 구조
- **중앙 허브 (EXAONE)**: 유문작업만 수행
- **브랜치 에이전트**: 각각 특화된 작업 수행
- **독립성**: 브랜치들은 서로 독립적

### 2. Repository 패턴
- **AgentRepository**: 브랜치 에이전트 관리 추상화
- **어댑터 패턴**: 각 브랜치를 어댑터로 래핑
- **확장성**: 새로운 브랜치 추가 용이

### 3. Orchestrator 패턴
- **Controller**: Orchestrator 사용
- **파이프라인 조율**: 전체 흐름 관리
- **관심사 분리**: 각 컴포넌트 독립적

### 4. Gateway 전략 (규칙기반 우선 + LLM 보조)
- **1차**: 규칙 기반 (80% 케이스)
- **2차**: KoELECTRA 필터 (15% 케이스)
- **3차**: LLM 보조 (5% 케이스)
- **비용 효율**: LLM은 모호한 경우만 호출

---

## 📈 성능 특성

### 처리 시간 (예상)
- 규칙 기반 결정: < 10ms
- KoELECTRA 필터: ~50ms
- 브랜치 에이전트: ~100ms (브랜치별 상이)
- EXAONE 허브: ~500ms
- LLM 보조 게이트: ~1000ms

### 비용 효율
- LLM 호출: 전체 요청의 약 5%만
- 평균 지연: 규칙 기반이 대부분이므로 < 100ms
- 토큰 사용량: 최소화 (LLM은 예외 처리만)

---

## 🔧 확장 방법

### 새로운 브랜치 에이전트 추가

1. **어댑터 생성**:
```python
# backend/services/branch_agents/new_adapter.py
from backend.services.branch_agents.base_adapter import BaseBranchAdapter
from backend.services.mcp_hub.ontology import AgentBranch

class NewAdapter(BaseBranchAdapter):
    def __init__(self):
        super().__init__(AgentBranch.NEW_BRANCH)

    async def execute(self, text: str, metadata=None):
        # 구현
        return self._create_result(result={...}, confidence=0.8)
```

2. **온톨로지에 브랜치 추가**:
```python
# backend/services/mcp_hub/ontology.py
class AgentBranch(str, Enum):
    NEW_BRANCH = "new_branch"
```

3. **Repository에 등록**:
```python
# backend/repository/agent_repository.py
from backend.services.branch_agents.new_adapter import NewAdapter
self._adapters[AgentBranch.NEW_BRANCH] = NewAdapter()
```

4. **규칙 추가** (선택):
```python
# backend/services/mcp_hub/ontology.py
OntologyRule(
    rule_id="rule_new_branch",
    priority=75,
    condition=r"새로운_패턴",
    action=ActionType.ROUTE,
    target_branch=AgentBranch.NEW_BRANCH
)
```

---

## 📝 요약

스타형 MCP 구조는 다음과 같이 작동합니다:

1. **Controller**: HTTP 요청/응답 처리 및 세션 관리
2. **Orchestrator**: 전체 파이프라인 조율
3. **Gateway Strategy**: 규칙기반 우선 + LLM 보조로 라우팅 결정
4. **Agent Repository**: 브랜치 에이전트 관리 및 실행
5. **EXAONE Star Hub**: 브랜치 결과를 받아 유문작업 수행

**핵심**: EXAONE은 중앙 허브로 유문작업만 수행하고, 각 브랜치 에이전트는 독립적으로 특화된 작업을 수행합니다.

