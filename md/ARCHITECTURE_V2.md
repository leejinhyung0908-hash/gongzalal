# 스타형 MCP 아키텍처 v2

## 📋 목차

1. [아키텍처 개요](#아키텍처-개요)
2. [핵심 설계 원칙](#핵심-설계-원칙)
3. [그래프 구조](#그래프-구조)
4. [노드 상세](#노드-상세)
5. [데이터 흐름](#데이터-흐름)
6. [순환 구조](#순환-구조)
7. [정책 기반 결정](#정책-기반-결정)
8. [모델 사용 전략](#모델-사용-전략)

---

## 아키텍처 개요

### 스타형 MCP (Model Context Protocol) 구조

**정책 기반 AI 에이전트 시스템**으로, KoELECTRA를 Gateway로 사용하고, EXAONE LLM이 맥락을 분석하여 최적의 브랜치 에이전트를 동적으로 선택합니다.

### 핵심 특징

- **KoELECTRA Gateway**: 빠른 1차 필터링 (스팸 확률 계산)
- **정책 기반 결정**: EXAONE LLM이 맥락 분석하여 노드 선택
- **순환 구조**: Branch → EXAONE → Branch 반복 가능
- **LangGraph 기반**: 정책 기반으로 매 노드마다 경로 분기
- **스타형 구조**: 중앙 허브(EXAONE) + 5개 브랜치 에이전트

---

## 핵심 설계 원칙

### 1. KoELECTRA Gateway 전략

```
KoELECTRA 1차 필터
  ├─ spam_prob < 0.3 → 즉시 allow (EXAONE LLM 호출 안 함)
  ├─ spam_prob > 0.8 → 즉시 deny (EXAONE LLM 호출 안 함)
  └─ 0.3 <= spam_prob <= 0.8 → EXAONE LLM 정책 결정
```

**장점**:
- 빠른 처리: 명확한 경우 즉시 결정
- 비용 절감: EXAONE LLM은 애매한 경우만 호출
- 정확도 향상: KoELECTRA 결과를 맥락에 포함

### 2. 정책 기반 결정

- **규칙은 참고용**: OntologyManager의 규칙은 참고용으로만 사용
- **AI 모델이 최종 결정**: EXAONE LLM이 맥락 분석하여 결정
- **동적 선택**: Context-aware 라우팅

### 3. 순환 구조 지원

- **Branch → EXAONE → Branch**: 추가 분석이 필요한 경우 순환
- **조건부 순환**: EXAONE 허브가 추가 브랜치 필요 여부 판단
- **무한 루프 방지**: `next_branches` 리스트로 제어

---

## 그래프 구조

### 전체 그래프 다이어그램 (Star Topology)

```
                    START
                      ↓
            ┌─────────────────────┐
            │   Gateway 노드       │
            │ (KoELECTRA 1차 필터) │
            └─────────────────────┘
                      ↓
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
    [deny]        [allow]        [route]
        ↓             ↓             ↓
       END    ┌──────────────┐  ┌──────────────┐
              │ EXAONE Hub    │  │Branch Router │
              │ (중앙 허브)     │  └──────────────┘
              └──────────────┘         ↓
                      ↓         ┌──────┼──────┬──────┬──────┐
                      ↓         ↓      ↓      ↓      ↓      ↓
                      ↓      spam  sentiment summary class notify
                      ↓         ↓      ↓      ↓      ↓      ↓
                      ↓         └──────┼──────┼──────┼──────┘
                      ↓                ↓
                      ↓         ┌──────────────┐
                      ↓         │ EXAONE Hub    │
                      ↓         │ (중앙 허브)     │
                      ↓         │ Star Topology │
                      ↓         └──────────────┘
                      ↓                ↓
                      ↓         ┌─────┼─────┐
                      ↓         ↓           ↓
                      ↓       end    branch_router
                      ↓         ↓      (순환)
                      ↓        END         ↓
                      ↓              ┌─────┼─────┐
                      ↓              ↓     ↓     ↓
                      ↓            spam sentiment ...
                      ↓              ↓     ↓     ↓
                      ↓              └─────┼─────┘
                      ↓                    ↓
                      ↓            ┌──────────────┐
                      ↓            │ EXAONE Hub    │
                      ↓            │ (중앙 허브)     │
                      ↓            └──────────────┘
                      ↓                    ↓
                      ↓              (계속 순환 가능)
                      ↓
                    END
```

### Star Topology 구조

```
                    ┌─────────────┐
                    │ EXAONE Hub  │
                    │ (중앙 허브)   │
                    └─────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ↓                 ↓                 ↓
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │ Spam     │      │Sentiment │      │ Summary  │
  │ Filter   │      │          │      │          │
  └──────────┘      └──────────┘      └──────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                    ┌─────────────┐
                    │ EXAONE Hub  │
                    │ (중앙 허브)   │
                    └─────────────┘
                          │
                    (다른 브랜치로)
```

**특징**:
- 모든 브랜치는 중앙 허브(EXAONE)를 거쳐야만 다른 브랜치로 이동
- 브랜치 간 직접 연결 없음
- 중앙 허브가 모든 라우팅 결정

### 상세 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│                    Gateway 노드                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 1. KoELECTRA 1차 필터 실행                            │  │
│  │    - spam_prob 계산                                    │  │
│  └─────────────────────────────────────────────────────┘  │
│                      ↓                                      │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 2. 분기 결정                                         │  │
│  │    - spam_prob < 0.3 → allow (EXAONE LLM 호출 안 함) │  │
│  │    - spam_prob > 0.8 → deny (EXAONE LLM 호출 안 함)  │  │
│  │    - 0.3 <= spam_prob <= 0.8 → EXAONE LLM 정책 결정 │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                      ↓
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
    [deny]        [allow]        [route]
        ↓             ↓             ↓
       END    ┌──────────────┐  ┌──────────────┐
              │ EXAONE Hub    │  │Branch Router │
              │ (유문작업)     │  └──────────────┘
              └──────────────┘         ↓
                      ↓         [브랜치 선택]
                      ↓                ↓
                      ↓         ┌──────┼──────┐
                      ↓         ↓      ↓      ↓
                      ↓      spam  sentiment ...
                      ↓         ↓      ↓      ↓
                      ↓         └──────┼──────┘
                      ↓                ↓
                      ↓         ┌──────────────┐
                      ↓         │ EXAONE Hub    │
                      ↓         │ (유문작업)     │
                      ↓         └──────────────┘
                      ↓                ↓
                      ↓         ┌─────┼─────┐
                      ↓         ↓           ↓
                      ↓       end    branch_router
                      ↓         ↓      (순환)
                      ↓        END         ↓
                      ↓              (다시 Branch로)
                      ↓
                    END
```

### 노드 구성

1. **Gateway 노드**: KoELECTRA 1차 필터 + EXAONE LLM 정책 결정
2. **Branch Router 노드**: 브랜치 선택 (순환 구조 지원)
3. **브랜치 노드** (5개):
   - `spam_filter`: KoELECTRA 사용
   - `sentiment`: 감정 분석
   - `summary`: 요약
   - `classification`: 분류
   - `notification`: 알림
4. **EXAONE Hub 노드**: 유문작업 + 추가 브랜치 필요 여부 판단

---

## 노드 상세

### 1. Gateway 노드

**파일**: `services/orchestrator/star_mcp_graph.py::gateway_node()`

**역할**: KoELECTRA를 1차 필터로 사용하는 게이트웨이

**처리 흐름**:
```
1. KoELECTRA 1차 필터 실행
   - spam_prob 계산

2. spam_prob에 따른 분기:
   - spam_prob < 0.3 → 즉시 allow (EXAONE LLM 호출 안 함)
   - spam_prob > 0.8 → 즉시 deny (EXAONE LLM 호출 안 함)
   - 0.3 <= spam_prob <= 0.8 → EXAONE LLM 정책 결정
      ↓
      - PolicyBasedRouter 호출
      - KoELECTRA 결과를 맥락에 포함
      - EXAONE LLM이 최종 결정
```

**출력**:
- `gateway_action`: "deny" | "allow" | "route"
- `target_branch`: 선택된 브랜치 (route인 경우)
- `gateway_confidence`: "low" | "medium" | "high"
- `gateway_reason_code`: 결정 근거

### 2. Branch Router 노드

**파일**: `services/orchestrator/star_mcp_graph.py::branch_router_node()`

**역할**: 브랜치 선택 (순환 구조 지원)

**처리 흐름**:
```
1. 순환 구조 확인
   - next_branches가 있으면 우선 사용
   - 사용한 브랜치는 제거

2. 일반적인 경우
   - target_branch 사용
   - 기본값: spam_filter
```

**순환 구조 지원**:
- EXAONE 허브에서 돌아온 경우 `next_branches` 우선 사용
- 여러 브랜치를 순차적으로 실행 가능

### 3. 브랜치 노드들

#### Spam Filter 브랜치
- **모델**: KoELECTRA
- **역할**: 스팸 확률 계산
- **출력**: `spam_prob`, `label`, `confidence`

#### Sentiment 브랜치
- **모델**: (스텁)
- **역할**: 감정 분석
- **출력**: 감정 분석 결과

#### Summary 브랜치
- **모델**: (스텁)
- **역할**: 요약
- **출력**: 요약 결과

#### Classification 브랜치
- **모델**: (스텁)
- **역할**: 텍스트 분류
- **출력**: 분류 결과

#### Notification 브랜치
- **모델**: (스텁)
- **역할**: 알림 전송
- **출력**: 알림 결과

### 4. EXAONE Hub 노드 (중앙 허브)

**파일**: `services/orchestrator/star_mcp_graph.py::exaone_hub_node()`

**역할**: Star Topology의 중앙 허브

**Star Topology 구조**:
- 모든 브랜치는 중앙 허브(EXAONE)를 거쳐야만 다른 브랜치로 이동
- 중앙 허브가 모든 라우팅 결정을 내림
- 브랜치 간 직접 연결 없음

**처리 흐름**:
```
1. 브랜치 결과 수집
   - AgentResult 객체로 변환
   - 현재까지 실행된 브랜치 목록 추적

2. EXAONE 유문작업
   - 브랜치 결과를 받아 글 다듬기
   - 최종 출력 생성

3. 다음 브랜치 결정 (Star Topology 라우팅)
   - PolicyBasedRouter 호출
   - 현재 결과와 EXAONE 출력을 맥락에 포함
   - 이미 실행된 브랜치는 제외
   - 다음에 실행할 브랜치 결정

4. 순환 구조 결정
   - needs_more_branches: True/False
   - next_branches: 다음에 실행할 브랜치 목록
   - target_branch: 다음 브랜치로 업데이트
```

**출력**:
- `final_output`: 다듬어진 최종 텍스트
- `needs_more_branches`: 추가 브랜치 필요 여부
- `next_branches`: 다음 브랜치 목록
- `target_branch`: 다음 브랜치 (업데이트)
- `completed`: 완료 여부

---

## 데이터 흐름

### 시나리오 1: 명확한 스팸 (즉시 차단)

```
입력: "긴급! 계정 정보가 유출되었습니다."

1. Gateway 노드
   - KoELECTRA: spam_prob = 0.95
   - spam_prob > 0.8 → 즉시 deny
   - EXAONE LLM 호출 안 함

2. route_after_gateway() → "end"

3. END
```

**처리 시간**: ~50ms (KoELECTRA만)
**비용**: EXAONE LLM 호출 없음

---

### 시나리오 2: 정상 메일 (즉시 허용)

```
입력: "안녕하세요. 다음 주 회의 시간 조율 부탁드립니다."

1. Gateway 노드
   - KoELECTRA: spam_prob = 0.15
   - spam_prob < 0.3 → 즉시 allow
   - EXAONE LLM 호출 안 함

2. route_after_gateway() → "exaone_hub"

3. EXAONE 허브
   - 브랜치 결과 없음
   - 원본 텍스트만으로 유문작업

4. route_after_exaone_hub() → "end"

5. END
```

**처리 시간**: ~550ms (KoELECTRA + EXAONE 허브)
**비용**: EXAONE LLM 1회 호출 (유문작업만)

---

### 시나리오 3: 애매한 케이스 (정책 결정 + 순환)

```
입력: "불만이 많아서 화가 납니다. 이 서비스는 최악입니다."

1. Gateway 노드
   - KoELECTRA: spam_prob = 0.45
   - 0.3 <= spam_prob <= 0.8 → EXAONE LLM 정책 결정
   - PolicyBasedRouter 호출
   - EXAONE LLM 결정: route → sentiment

2. route_after_gateway() → "branch_router"

3. Branch Router
   - target_branch = "sentiment"

4. Sentiment 브랜치 실행
   - 감정 분석 수행

5. EXAONE 허브
   - Sentiment 결과를 받아 유문작업
   - 추가 분석 필요 판단
   - PolicyBasedRouter 호출
   - EXAONE LLM 결정: 추가 브랜치 필요 → spam_filter
   - next_branches = ["spam_filter"]

6. route_after_exaone_hub() → "branch_router" (순환)

7. Branch Router (순환)
   - next_branches에서 "spam_filter" 선택

8. Spam Filter 브랜치 실행
   - KoELECTRA로 스팸 확률 계산

9. EXAONE 허브
   - Spam Filter + Sentiment 결과를 받아 유문작업
   - 추가 브랜치 없음

10. route_after_exaone_hub() → "end"

11. END
```

**처리 시간**: ~1.5초 (KoELECTRA + EXAONE LLM 2회 + 브랜치 2개)
**비용**: EXAONE LLM 3회 호출 (정책 결정 2회 + 유문작업 2회)

---

## 순환 구조 (Star Topology)

### Star Topology 순환 구조

**목적**: 중앙 허브(EXAONE)를 거쳐 각 브랜치들을 왔다 갔다 할 수 있는 구조

**특징**:
- **중앙 허브 중심**: 모든 브랜치는 중앙 허브(EXAONE)를 거쳐야만 다른 브랜치로 이동
- **브랜치 간 직접 연결 없음**: 브랜치들은 서로 직접 연결되지 않음
- **중앙 허브가 라우팅 결정**: EXAONE 허브가 다음 브랜치를 결정

### 순환 흐름 (Star Topology)

```
[Branch 1] → [EXAONE Hub (중앙)] → [Branch Router] → [Branch 2] → [EXAONE Hub (중앙)] → [Branch Router] → [Branch 3] → ...
```

**다이어그램**:
```
    Branch A
        ↓
    EXAONE Hub (중앙 허브)
        ↓
    Branch Router
        ↓
    Branch B
        ↓
    EXAONE Hub (중앙 허브)
        ↓
    Branch Router
        ↓
    Branch C
        ↓
    EXAONE Hub (중앙 허브)
        ↓
    END
```

### 순환 조건

```python
# EXAONE 중앙 허브에서 판단
if needs_more_branches and next_branches:
    return "branch_router"  # 중앙 허브를 거쳐 다른 브랜치로
else:
    return "end"  # 종료
```

### 무한 루프 방지

1. **next_branches 리스트**: 실행할 브랜치 목록 관리
2. **실행된 브랜치 추적**: `executed_branches`로 이미 실행된 브랜치 제외
3. **조건부 순환**: EXAONE 허브가 필요할 때만 순환
4. **중앙 허브 결정**: EXAONE 허브가 모든 라우팅 결정

### 순환 예시 (Star Topology)

```
1. Gateway → sentiment 선택
2. Sentiment 브랜치 실행
   ↓
3. EXAONE 중앙 허브
   - 감정 분석 결과 확인
   - 유문작업 수행
   - 다음 브랜치 결정: spam_filter
   - next_branches = ["spam_filter"]
   ↓
4. Branch Router (중앙 허브를 거쳐)
   - spam_filter 선택
   ↓
5. Spam Filter 브랜치 실행
   ↓
6. EXAONE 중앙 허브
   - Spam Filter + Sentiment 결과 종합
   - 유문작업 수행
   - 추가 브랜치 없음 판단
   ↓
7. END
```

### Star Topology의 장점

1. **중앙 집중식 제어**: 모든 라우팅 결정이 중앙 허브에서 이루어짐
2. **유연한 라우팅**: 중앙 허브가 맥락을 보고 최적의 브랜치 선택
3. **확장성**: 새로운 브랜치 추가가 용이 (중앙 허브만 수정)
4. **일관성**: 모든 브랜치가 중앙 허브를 거치므로 일관된 처리

---

## 정책 기반 결정

### PolicyBasedRouter

**파일**: `services/orchestrator/policy_based_router.py`

**역할**: AI 모델이 맥락을 분석하여 최적의 노드 선택

### 결정 프로세스

```
1. 규칙 제안 수집 (참고용)
   - OntologyManager.evaluate_rules()
   - 상위 3개 규칙만 사용

2. 맥락 정보 수집
   - 세션 정보
   - 사용자 정보
   - KoELECTRA 결과 (Gateway에서 호출된 경우)
   - 현재 브랜치 결과 (EXAONE 허브에서 호출된 경우)
   - EXAONE 출력 (EXAONE 허브에서 호출된 경우)

3. EXAONE LLM 호출
   - 맥락을 포함한 프롬프트 구성
   - JSON 형식으로 결정 요청

4. JSON 파싱 및 반환
   - action: deny/allow/route
   - target_branch: 선택된 브랜치
   - additional_branches: 추가 브랜치 목록
   - confidence: 신뢰도
   - reason: 결정 근거
```

### 프롬프트 구조

```
당신은 스타형 MCP 구조의 중앙 허브(Hub)입니다.

사용자 입력: {text}

사용 가능한 브랜치 에이전트:
- spam_filter: 스팸 필터링
- sentiment: 감정 분석
- summary: 요약
- classification: 분류
- notification: 알림

규칙 기반 제안 (참고용):
{rule_summary}

KoELECTRA 1차 필터 결과 (애매한 경우):
- 스팸 확률: {spam_prob}
- 라벨: {label}
- 신뢰도: {confidence}

추가 맥락 정보:
{context}

요구사항:
1. 사용자의 요청을 분석하여 목표를 파악하세요.
2. 각 브랜치 에이전트의 역할을 고려하여 최적의 노드를 선택하세요.
3. 규칙 제안은 참고용이며, 최종 결정은 당신의 판단에 따라 내리세요.
4. 여러 브랜치가 필요할 수 있습니다.
5. 명확한 스팸/악성 콘텐츠는 즉시 차단하세요.

JSON 형식으로만 답변:
{
  "action": "deny" | "allow" | "route",
  "target_branch": "spam_filter" | ... | null,
  "reason": "선택 근거",
  "confidence": 0.0~1.0,
  "additional_branches": ["branch1", "branch2"]
}
```

---

## 모델 사용 전략

### 모델 사용 위치

| 위치 | 모델 | 용도 | 호출 조건 |
|------|------|------|----------|
| **Gateway 노드** | KoELECTRA | 1차 필터 | 항상 |
| **Gateway 노드** | EXAONE LLM | 정책 결정 | spam_prob 0.3~0.8 (애매한 경우) |
| **Spam Filter 브랜치** | KoELECTRA | 스팸 확률 계산 | spam_filter 브랜치 실행 시 |
| **EXAONE 허브** | EXAONE LLM | 유문작업 | 항상 (브랜치 실행 후) |
| **EXAONE 허브** | EXAONE LLM | 추가 브랜치 판단 | 순환 구조 지원 시 |

### 비용 최적화

1. **KoELECTRA 우선**: 빠르고 저렴한 1차 필터
2. **EXAONE LLM 선택적 호출**: 애매한 경우만 호출
3. **명확한 경우 즉시 결정**: EXAONE LLM 호출 없음

### 성능 특성

| 케이스 | KoELECTRA | EXAONE LLM | 총 처리 시간 |
|--------|-----------|------------|-------------|
| 명확한 스팸 | 1회 | 0회 | ~50ms |
| 정상 메일 | 1회 | 1회 (유문작업) | ~550ms |
| 애매한 케이스 | 1~2회 | 2~3회 | ~1.5초 |

---

## State 구조

### StarMcpState

```python
class StarMcpState(TypedDict):
    # 메시지 히스토리
    messages: list[BaseMessage]

    # 입력 정보
    text: str
    request_id: str
    metadata: dict

    # Gateway 결정
    gateway_action: Optional[Literal["deny", "allow", "route"]]
    target_branch: Optional[str]
    gateway_confidence: Optional[Literal["low", "medium", "high"]]
    gateway_reason_code: Optional[str]

    # 브랜치 에이전트 결과
    branch_results: list[dict]

    # EXAONE 허브 결과
    final_output: Optional[str]

    # 순환 구조 지원
    needs_more_branches: Optional[bool]
    next_branches: Optional[list[str]]

    # 최종 상태
    completed: bool
```

---

## 라우팅 함수

### 1. route_after_gateway()

**역할**: Gateway 노드 이후 라우팅

```python
def route_after_gateway(state: StarMcpState) -> str:
    action = state.get("gateway_action")
    if action == "deny":
        return "end"
    elif action == "allow":
        return "exaone_hub"
    elif action == "route":
        return "branch_router"
```

### 2. route_after_branch_router()

**역할**: Branch Router 노드 이후 브랜치 선택

```python
def route_after_branch_router(state: StarMcpState) -> str:
    target_branch = state.get("target_branch")
    return branch_map.get(target_branch, "spam_filter")
```

### 3. route_after_branch()

**역할**: 브랜치 노드 이후 EXAONE 허브로

```python
def route_after_branch(state: StarMcpState) -> str:
    return "exaone_hub"
```

### 4. route_after_exaone_hub()

**역할**: EXAONE 허브 이후 순환 또는 종료

```python
def route_after_exaone_hub(state: StarMcpState) -> str:
    needs_more = state.get("needs_more_branches", False)
    next_branches = state.get("next_branches", [])

    if needs_more and next_branches:
        return "branch_router"  # 순환
    else:
        return "end"  # 종료
```

---

## 확장 방법

### 새로운 브랜치 추가

1. **어댑터 생성** (`services/branch_agents/new_adapter.py`)
2. **온톨로지에 추가** (`services/mcp_hub/ontology.py`)
3. **Repository에 등록** (`repository/agent_repository.py`)
4. **그래프에 노드 추가** (`services/orchestrator/star_mcp_graph.py`)
5. **라우팅 함수 업데이트** (`route_after_branch_router()`)

### 순환 구조 커스터마이징

1. **EXAONE 허브 로직 수정**: `exaone_hub_node()`에서 순환 조건 변경
2. **PolicyBasedRouter 프롬프트 수정**: 추가 브랜치 판단 기준 변경
3. **무한 루프 방지**: 최대 순환 횟수 제한 추가

---

## 컴포넌트 간 상호작용

### 컴포넌트 계층 구조

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Layer                        │
│  - mcp_router.py: HTTP 엔드포인트                       │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│                  Controller Layer                       │
│  - mcp_controller.py: 비즈니스 로직, 세션 관리           │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│                Orchestrator Layer                       │
│  - mcp_orchestrator.py: LangGraph 실행                  │
│  - star_mcp_graph.py: 그래프 정의                        │
│  - policy_based_router.py: 정책 기반 라우터             │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│                  Service Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │   MCP Hub       │  │   Star Hub      │              │
│  │ - ontology.py    │  │ - exaone_hub.py │              │
│  │ - gateway_      │  │                 │              │
│  │   strategy.py   │  │                 │              │
│  └─────────────────┘  └─────────────────┘              │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Branch Agents   │  │  Repository     │              │
│  │ - spam_filter   │  │ - agent_        │              │
│  │ - sentiment     │  │   repository.py │              │
│  │ - summary       │  │                 │              │
│  │ - ...           │  │                 │              │
│  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

### 데이터 흐름 상세

```
[HTTP Request]
    ↓
[Controller]
    ├─ 세션 ID 생성
    ├─ 요청 검증
    └─ Orchestrator 호출
        ↓
[Orchestrator]
    └─ LangGraph 실행
        ↓
[Gateway 노드]
    ├─ KoELECTRA 실행 (항상)
    ├─ spam_prob < 0.3 → allow
    ├─ spam_prob > 0.8 → deny
    └─ 0.3 <= spam_prob <= 0.8 → EXAONE LLM 정책 결정
        ↓
[정책 기반 분기]
    ├─ deny → END
    ├─ allow → EXAONE Hub
    └─ route → Branch Router
        ↓
[Branch Router]
    ├─ next_branches 우선 사용 (순환 구조)
    └─ target_branch 사용 (일반)
        ↓
[브랜치 노드]
    ├─ AgentRepository.get_adapter()
    ├─ adapter.execute()
    └─ 결과를 branch_results에 추가
        ↓
[EXAONE Hub]
    ├─ 브랜치 결과 수집
    ├─ EXAONE 유문작업
    ├─ 추가 브랜치 필요 여부 판단
    └─ PolicyBasedRouter 호출 (필요시)
        ↓
[순환 또는 종료]
    ├─ needs_more_branches → Branch Router (순환)
    └─ 완료 → END
```

---

## 요약

이 아키텍처는 **KoELECTRA Gateway + 정책 기반 순환 구조**를 가진 스타형 MCP 시스템입니다.

### 핵심 특징

1. **KoELECTRA Gateway**: 빠른 1차 필터링
2. **정책 기반 결정**: EXAONE LLM이 맥락 분석하여 노드 선택
3. **순환 구조**: Branch → EXAONE → Branch 반복 가능
4. **LangGraph 기반**: 정책 기반으로 매 노드마다 경로 분기

### 처리 전략

- **명확한 경우**: KoELECTRA만으로 즉시 결정 (80% 케이스)
- **애매한 경우**: EXAONE LLM으로 정책 결정 (20% 케이스)
- **추가 분석**: 순환 구조로 추가 브랜치 실행

### 성능 및 비용

| 케이스 | KoELECTRA | EXAONE LLM | 처리 시간 | 비용 |
|--------|-----------|------------|----------|------|
| 명확한 스팸 | 1회 | 0회 | ~50ms | 낮음 |
| 정상 메일 | 1회 | 1회 | ~550ms | 중간 |
| 애매한 케이스 | 1~2회 | 2~3회 | ~1.5초 | 높음 |

### 아키텍처 원칙

1. **Gateway 우선**: KoELECTRA로 빠른 필터링
2. **정책 기반**: AI 모델이 맥락 분석하여 결정
3. **순환 구조**: 추가 분석이 필요한 경우 순환
4. **스타형 구조**: 중앙 허브(EXAONE) + 브랜치 에이전트

