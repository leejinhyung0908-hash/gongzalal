# Admin Services

> Admin 도메인의 핵심 서비스 모듈

```
services/
├── __init__.py
├── exaone_hub.py         # EXAONE 중앙 허브 (스타 노드)
├── gateway_strategy.py   # 게이트웨이 전략 (규칙+LLM 하이브리드)
├── graph_v2.py           # KoELECTRA 게이트웨이 (LangGraph)
└── ontology.py           # 온톨로지/정책 정의
```

---

## 📦 모듈 설명

### 1. `exaone_hub.py` - EXAONE 중앙 허브

**역할**: 스타 토폴로지의 **중앙 허브 (Star Node)**

```python
class ExaoneHub:
    """EXAONE 중앙 허브 - 유문작업(글 다듬기) 담당"""
```

| 메서드 | 설명 |
|--------|------|
| `refine_output()` | 브랜치 에이전트 결과를 받아 최종 출력 생성 |
| `_summarize_branch_results()` | 브랜치 결과 요약 |

**주요 기능**:
- 각 브랜치 에이전트의 결과를 종합
- EXAONE LLM으로 최종 출력 다듬기
- 일관성 있는 응답 생성

---

### 2. `gateway_strategy.py` - 게이트웨이 전략

**역할**: **규칙기반 우선 + LLM 보조** 하이브리드 전략

```python
class GatewayStrategy:
    """게이트웨이 전략 (규칙기반 우선 + LLM 보조)"""
```

| 메서드 | 설명 |
|--------|------|
| `process_request()` | 요청 처리 (3단계 전략) |
| `_rule_based_gate()` | 1차: 온톨로지 규칙 평가 |
| `_koelectra_gate()` | 2차: KoELECTRA 필터링 |
| `_llm_assisted_gate()` | 3차: LLM 보조 (예외 처리) |

**처리 전략**:
```
1. 규칙기반 게이트 (1차 필터)
   └─ 온톨로지 규칙 평가 → 빠른 결정

2. KoELECTRA 게이트 (2차 필터)
   └─ 스팸 확률 기반 판정

3. LLM 보조 게이트 (예외 처리)
   └─ 규칙이 모호한 경우만 호출
```

---

### 3. `graph_v2.py` - KoELECTRA 게이트웨이

**역할**: **KoELECTRA 1차 필터** + LangGraph 기반 워크플로우

```python
@tool
def mcp_tool_koelectra_filter(text: str) -> dict:
    """KoELECTRA 스팸 필터 도구"""
```

| 컴포넌트 | 설명 |
|----------|------|
| `mcp_tool_koelectra_filter` | KoELECTRA 스팸 분류 도구 |
| `GatewayDecision` | 게이트웨이 결정 스키마 |
| `PolicyRule` | 정책 규칙 스키마 |

**정책 인터페이스**:
```python
class GatewayDecision(TypedDict):
    action: Literal["allow", "deny", "quarantine", "route"]
    confidence: Literal["high", "medium", "low"]
    reason_code: str
    target_branch: Optional[str]
    user_message: str
```

**KoELECTRA 임계값**:
```
spam_prob < 0.3  → ALLOW (정상)
spam_prob > 0.8  → DENY (스팸)
0.3 ~ 0.8        → EXAONE 판별기 사용
```

---

### 4. `ontology.py` - 온톨로지 관리

**역할**: 스타형 MCP 구조의 **온톨로지/정책 정의**

```python
class AgentBranch(str, Enum):
    """브랜치 에이전트 타입"""
    SPAM_FILTER = "spam_filter"
    SENTIMENT = "sentiment"
    SUMMARY = "summary"
    CLASSIFICATION = "classification"
    NOTIFICATION = "notification"

class ActionType(str, Enum):
    """게이트웨이 액션 타입"""
    ALLOW = "allow"
    DENY = "deny"
    ROUTE = "route"
    QUARANTINE = "quarantine"
    ASK_USER = "ask_user"

class ConfidenceLevel(str, Enum):
    """신뢰도 레벨"""
    LOW = "low"      # < 0.5
    MEDIUM = "medium"  # 0.5 ~ 0.7
    HIGH = "high"    # > 0.7
```

| 클래스 | 설명 |
|--------|------|
| `AgentBranch` | 브랜치 에이전트 타입 (Enum) |
| `ActionType` | 게이트웨이 액션 타입 (Enum) |
| `ConfidenceLevel` | 신뢰도 레벨 (Enum) |
| `OntologyRule` | 온톨로지 규칙 (Dataclass) |
| `RoutingPolicy` | 라우팅 정책 (Dataclass) |
| `OntologyManager` | 온톨로지 관리자 |

---

## 🔄 데이터 플로우

```
┌─────────────────────────────────────────────────────────────┐
│                     Gateway Strategy                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ 1. 규칙기반  │───▶│ 2. KoELECTRA │───▶│ 3. LLM 보조  │  │
│  │    게이트    │    │    게이트    │    │    게이트    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│        │                   │                   │           │
│        ▼                   ▼                   ▼           │
│   ┌─────────┐         ┌─────────┐         ┌─────────┐     │
│   │ ALLOW   │         │ DENY    │         │ ROUTE   │     │
│   │ DENY    │         │ ALLOW   │         │ (브랜치)│     │
│   └─────────┘         └─────────┘         └─────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   EXAONE Hub    │
                    │  (유문작업/최종)  │
                    └─────────────────┘
```

---

## 📊 의존성 관계

```
ontology.py
    │
    ├──▶ gateway_strategy.py
    │         │
    │         └──▶ graph_v2.py (KoELECTRA)
    │
    └──▶ exaone_hub.py
              │
              └──▶ core/llm/providers/ (EXAONE)
```

---

## 🔗 외부 의존성

| 모듈 | 의존 대상 |
|------|----------|
| `exaone_hub.py` | `backend.dependencies.get_llm` |
| `gateway_strategy.py` | `graph_v2.mcp_tool_koelectra_filter` |
| `graph_v2.py` | `transformers`, `peft`, `langgraph` |
| `ontology.py` | (독립적) |

