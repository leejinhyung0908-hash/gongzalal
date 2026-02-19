# Backend Architecture Document

## 📋 개요

본 문서는 **Spam Filter RAG Backend**의 전체 아키텍처를 설명합니다.

### 핵심 설계 원칙

| 원칙 | 설명 |
|------|------|
| **Vertical Slicing** | 각 도메인은 독립적인 Agent, Service, Schema, Repository를 보유 |
| **Star Topology** | 중앙 허브(EXAONE)를 통해 브랜치 간 통신 |
| **Policy-Based Routing** | 온톨로지 기반 정책으로 동적 라우팅 결정 |
| **Two-Stage Filtering** | KoELECTRA(빠른 필터) + EXAONE(정밀 판단) |

---

## 🏗️ 디렉토리 구조

```
backend/
├── main.py                    # FastAPI 애플리케이션 진입점
├── config.py                  # 환경설정 및 설정값 관리
├── dependencies.py            # FastAPI 의존성 주입
├── models.py                  # 공통 Pydantic 모델
├── requirements.txt           # Python 의존성
│
├── models/                    # [Shared Model Assets] 공유 모델 자산
│   ├── exaone/               # EXAONE 3.5B LLM
│   │   ├── exaone_model/     # 기본 모델 가중치
│   │   └── exaone_adapter/   # LoRA 어댑터
│   ├── koelectra/            # KoELECTRA 분류 모델
│   │   ├── spam/             # 스팸 분류 LoRA
│   │   └── callcenter/       # 콜센터 분류 LoRA
│   └── midm/                 # MiDM 모델 (예비)
│
├── ochestrator/               # [Application Coordination] 중앙 조율
│   └── mcp_ochestrator/
│       ├── mcp_orchestrator.py    # 메인 오케스트레이터
│       ├── mcp_controller.py      # MCP 컨트롤러
│       ├── policy_based_router.py # 정책 기반 라우터
│       └── star_mcp_graph.py      # LangGraph 스타 토폴로지
│
├── routes/                    # [Global API Interface] API 라우터
│   ├── mcp_router.py         # MCP 게이트웨이 API
│   ├── chat.py               # 채팅/RAG API
│   └── health.py             # 헬스체크 API
│
├── domain/                    # [Bounded Contexts] 도메인별 비즈니스 로직
│   ├── spam_classifier/      # 스팸 분류 도메인
│   │   ├── agents/
│   │   │   └── verdict_agent/
│   │   │       └── graph.py  # EXAONE LangGraph
│   │   ├── services/
│   │   │   ├── ontology.py           # 온톨로지/정책 정의
│   │   │   ├── graph_v2.py           # KoELECTRA 필터
│   │   │   ├── exaone_hub.py         # EXAONE 중앙 허브
│   │   │   ├── gateway_strategy.py   # 게이트웨이 전략
│   │   │   ├── spam_filter_adapter.py
│   │   │   ├── sentiment_adapter.py
│   │   │   ├── summary_adapter.py
│   │   │   ├── classification_adapter.py
│   │   │   └── notification_adapter.py
│   │   ├── spam_schemas/
│   │   │   ├── base_model.py    # 요청/응답 스키마
│   │   │   └── state_model.py   # 상태 스키마
│   │   └── repository/
│   │       └── agent_repository.py  # 브랜치 에이전트 저장소
│   │
│   ├── chat/                  # 대화 인터페이스 도메인
│   │   ├── agents/
│   │   ├── services/
│   │   │   ├── rag.py           # RAG 서비스
│   │   │   └── chat_service.py  # 채팅 서비스
│   │   └── repository/
│   │
│   └── training/              # 모델 학습 도메인
│       ├── agents/
│       ├── services/
│       │   ├── lora_adapter.py      # LoRA 학습
│       │   ├── train.py             # 학습 실행
│       │   ├── extract_jsonl.py     # 데이터 추출
│       │   └── ...
│       └── repository/
│
├── common/                    # [Cross-cutting Concerns] 공통 모듈
│   ├── llm/
│   │   ├── base.py           # LLM 추상 베이스 클래스
│   │   ├── loader.py         # 모델 로더
│   │   ├── registry.py       # 모델 레지스트리
│   │   ├── factory.py        # 모델 팩토리
│   │   ├── register_models.py
│   │   └── implementations/
│   │       ├── exaone_llm.py # EXAONE 구현체
│   │       └── midm_llm.py   # MiDM 구현체
│   └── utils/
│       ├── database.py       # DB 유틸리티
│       └── embedding.py      # 임베딩 유틸리티
│
└── data/                      # 데이터 파일
    └── spamdata/
```

---

## 📚 Star Topology 온톨로지 용어 정의

본 시스템에서 사용하는 핵심 용어들의 정의와 실제 코드 매핑입니다.

### 1. 오케스트레이터 (Orchestrator)

> **정의**: 전체 워크플로우의 **생애주기 관리자(Lifecycle Manager)**

| 항목 | 내용 |
|------|------|
| **역할** | 사용자 요청 → LangGraph StateGraph 생성/실행 → 세션 관리 → 에러 핸들링 → 최종 결과 반환 |
| **온톨로지적 의미** | 시스템의 '의지'와 '흐름'을 결정하는 **최상위 개체** |
| **구현 파일** | `ochestrator/mcp_ochestrator/mcp_orchestrator.py` |
| **클래스** | `McpOrchestrator` |

```python
# ochestrator/mcp_ochestrator/mcp_orchestrator.py
class McpOrchestrator:
    """MCP 오케스트레이터 (스타형 구조)"""

    def __init__(self):
        self.gateway_strategy = GatewayStrategy()    # 게이트웨이 전략
        self.agent_repository = AgentRepository()    # 브랜치 저장소
        self.exaone_hub = ExaoneHub()                # 스타 허브

    async def process_request(self, text: str, metadata: dict) -> dict:
        """LangGraph 기반 정책 분기 그래프 실행"""
        return await run_star_mcp_graph(text, request_id, metadata, thread_id)
```

---

### 2. 컨트롤러-게이트 (Controller-Gate Pattern)

> **정의**: **KoELECTRA 게이트 판정** + **에스컬레이션 결정**을 담당하는 계층

| 항목 | 내용 |
|------|------|
| **역할** | KoELECTRA로 1차 게이트 판정 → Short-circuit 또는 에스컬레이션 결정 |
| **온톨로지적 의미** | 데이터의 '진입 허가' 및 '에스컬레이션 여부'를 판별하는 **수문장** |
| **구현 파일** | `ochestrator/mcp_ochestrator/mcp_controller.py` |
| **클래스** | `McpController` |
| **핵심 원칙** | **Controller는 생성형 결과를 만들지 않음** (판정/라우팅만) |

```python
# ochestrator/mcp_ochestrator/mcp_controller.py
class McpController:
    """MCP Controller (게이트/에스컬레이션 판정)"""

    SPAM_PROB_LOW = 0.3   # 이 미만이면 즉시 ALLOW
    SPAM_PROB_HIGH = 0.8  # 이 초과면 즉시 DENY

    async def process_gateway_request(self, request):
        # 1단계: KoELECTRA 게이트 판정 (Controller 레벨)
        koelectra_result = self._get_koelectra_filter().invoke({"text": text})
        spam_prob = koelectra_result.get("spam_prob", 0.5)

        # 2단계: Short-circuit 판단
        if spam_prob < self.SPAM_PROB_LOW:
            # 🚀 Short-circuit: 즉시 ALLOW (EXAONE 호출 안 함)
            return GatewayResponse(gateway_action="deliver", ...)

        elif spam_prob > self.SPAM_PROB_HIGH:
            # 🚀 Short-circuit: 즉시 DENY (EXAONE 호출 안 함)
            return GatewayResponse(gateway_action="quarantine", ...)

        else:
            # 3단계: 에스컬레이션 (애매한 케이스만 EXAONE으로)
            orchestrator_result = await self._get_orchestrator().process_request(...)
            return GatewayResponse(exaone_used=True, ...)
```

**Controller-Gate 흐름도:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                     CONTROLLER (게이트/에스컬레이션)                  │
│                                                                     │
│  ┌──────────────┐                                                   │
│  │  KoELECTRA   │  ← 1차 게이트 판정 (~10ms)                         │
│  │  (Controller │                                                   │
│  │   레벨)      │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ spam_prob < 0.3 → 🚀 Short-circuit ALLOW (EXAONE 호출 안 함) │    │
│  │ spam_prob > 0.8 → 🚀 Short-circuit DENY  (EXAONE 호출 안 함) │    │
│  │ 0.3~0.8        → 🔄 에스컬레이션 (Orchestrator → EXAONE)     │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

**장점:**
- 명확한 케이스는 EXAONE 호출 없이 즉시 응답 (VRAM 절약)
- Controller가 게이트 역할을 명확히 담당
- 6GB VRAM 환경에서 효율적

---

### 3. 브랜치 노드 (Branch Nodes)

> **정의**: 특정 도메인에 특화된 **전문가 에이전트(Domain Specialists)** 군집

| 항목 | 내용 |
|------|------|
| **역할** | Spam, Sentiment, Summary, Classification 등 개별 비즈니스 로직 수행 |
| **온톨로지적 의미** | 수평적으로 확장 가능한 '기능적 단위'이자 '전문 지식'의 **원천** |
| **구현 경로** | `domain/spam_classifier/services/*_adapter.py` |
| **관리자** | `domain/spam_classifier/repository/agent_repository.py` |

```python
# domain/spam_classifier/services/ontology.py
class AgentBranch(str, Enum):
    SPAM_FILTER = "spam_filter"      # 🛡️ 스팸 상세 분석
    SENTIMENT = "sentiment"          # 😊 감정 분석
    SUMMARY = "summary"              # 📝 텍스트 요약
    CLASSIFICATION = "classification" # 🏷️ 텍스트 분류
    NOTIFICATION = "notification"    # 🔔 알림 처리
```

**브랜치 어댑터 구조:**
```
domain/spam_classifier/services/
├── base_adapter.py              # 추상 베이스 클래스
├── spam_filter_adapter.py       # SpamFilterAdapter
├── sentiment_adapter.py         # SentimentAdapter
├── summary_adapter.py           # SummaryAdapter
├── classification_adapter.py    # ClassificationAdapter
└── notification_adapter.py      # NotificationAdapter
```

```python
# domain/spam_classifier/repository/agent_repository.py
class AgentRepository:
    """에이전트 Repository (브랜치 에이전트 관리)"""

    def __init__(self):
        self._adapters: Dict[AgentBranch, IAgentAdapter] = {}
        self._load_adapters()  # 모든 브랜치 어댑터 로드

    async def execute_branch(self, branch: AgentBranch, text: str) -> AgentResult:
        """브랜치 에이전트 실행"""
        adapter = self.get_adapter(branch)
        return await adapter.execute(text)
```

---

### 4. 스타 노드 (Star Node / EXAONE Hub)

> **정의**: 별 모양 구조의 중심에 위치한 **중앙 지능 허브(Central Intelligence Hub)**

| 항목 | 내용 |
|------|------|
| **역할** | ① 유문작업(Output Refinement) ② 동적 라우팅(Next Action) 결정 |
| **온톨로지적 의미** | 정보의 '통합'과 '의사결정'을 담당하는 시스템의 **핵심 두뇌** |
| **구현 파일** | `domain/spam_classifier/services/exaone_hub.py` |
| **클래스** | `ExaoneHub` |

```python
# domain/spam_classifier/services/exaone_hub.py
class ExaoneHub:
    """EXAONE 중앙 허브 (스타)"""

    def __init__(self):
        self._llm = get_llm(model_name="backend/model/exaone", model_type="exaone")

    async def refine_output(
        self,
        text: str,
        branch_results: List[AgentResult],  # 브랜치 결과들
        metadata: dict
    ) -> str:
        """유문작업: 브랜치 결과를 자연스러운 문장으로 합성"""

        branch_summary = self._summarize_branch_results(branch_results)

        prompt = f"""다음 텍스트와 각 브랜치 에이전트의 분석 결과를 바탕으로,
        최종적으로 다듬어진 출력을 생성하세요.

        원본 텍스트: {text}
        브랜치 분석 결과: {branch_summary}
        """

        return self._llm.generate(prompt)
```

**Star Topology 순환 구조:**
```
                    ┌─────────────────────────┐
                    │      EXAONE HUB         │
                    │   (Central Intelligence) │
                    │                         │
        ┌──────────▶│  1. 유문작업 (Refine)   │◀──────────┐
        │           │  2. 다음 액션 결정       │           │
        │           └───────────┬─────────────┘           │
        │                       │                         │
        │            ┌──────────┴──────────┐              │
        │            ▼                     ▼              │
   ┌────────┐  ┌──────────┐          ┌──────────┐  ┌────────┐
   │ SPAM   │  │SENTIMENT │          │ SUMMARY  │  │ CLASS  │
   │ FILTER │  │ ANALYSIS │          │          │  │        │
   └────────┘  └──────────┘          └──────────┘  └────────┘
        │           │                     │              │
        └───────────┴──────────┬──────────┴──────────────┘
                               │
                      (결과를 허브로 전송)
```

---

### 5. 로라 어댑터 (LoRA Adapter)

> **정의**: 범용 모델에 특정 도메인 지식을 주입한 **미세 조정 가중치(Task-specific Weights)**

| 항목 | 내용 |
|------|------|
| **역할** | 기본 모델 변경 없이 특정 태스크 정확도 향상 + VRAM 절약 |
| **온톨로지적 의미** | 모델이 특정 상황에서 발휘하는 '숙련도' 또는 '**전문 스킬**' |
| **저장 경로** | `models/` 폴더 |
| **학습 도구** | `domain/training/services/lora_adapter.py` |

```
models/
├── exaone/
│   ├── exaone_model/           # 기본 EXAONE 가중치 (2.4B)
│   └── exaone_adapter/         # LoRA 어댑터 (스팸 판단 특화)
│       ├── adapter_config.json
│       ├── adapter_model.safetensors
│       └── checkpoint-*/       # 체크포인트들
│
├── koelectra/
│   ├── spam/
│   │   └── lora/               # 스팸 분류 LoRA
│   │       └── run_20260115_131534/
│   └── callcenter/
│       └── lora/               # 콜센터 분류 LoRA
│           └── run_20260115_130137/
```

**LoRA 설정 예시:**
```json
// models/koelectra/spam/lora/run_20260115_131534/adapter_config.json
{
  "base_model_name_or_path": "monologg/koelectra-small-v3-discriminator",
  "task_type": "SEQ_CLS",
  "r": 8,              // LoRA rank
  "lora_alpha": 16,    // LoRA alpha
  "lora_dropout": 0.1,
  "target_modules": ["query", "value"]
}
```

---

### 6. 저장소 (Repository)

> **정의**: 도메인별 데이터와 프롬프트, 세션 이력이 영구적으로 저장되는 **지식 창고(Knowledge Store)**

| 항목 | 내용 |
|------|------|
| **역할** | 브랜치 에이전트 관리 + RAG용 벡터 검색 데이터 보관 |
| **온톨로지적 의미** | 시스템이 학습하고 참조하는 '장기 기억'과 '**사실(Fact)**'의 집합 |
| **구현 경로** | `domain/*/repository/` |
| **Vector DB** | `common/utils/database.py` (pgvector) |

```python
# domain/spam_classifier/repository/agent_repository.py
class AgentRepository:
    """에이전트 Repository"""

    def __init__(self):
        self._adapters: Dict[AgentBranch, IAgentAdapter] = {}

    def _load_adapters(self):
        """각 브랜치 에이전트 어댑터 로드"""
        self._adapters[AgentBranch.SPAM_FILTER] = SpamFilterAdapter()
        self._adapters[AgentBranch.SENTIMENT] = SentimentAdapter()
        # ...

    def list_branches(self) -> list[AgentBranch]:
        """사용 가능한 브랜치 목록"""
        return list(self._adapters.keys())
```

```python
# common/utils/database.py (pgvector)
def search_similar(conn, query: str, top_k: int = 3) -> list:
    """RAG용 벡터 유사도 검색"""
    query_embedding = simple_embed(query)

    cur = conn.cursor()
    cur.execute("""
        SELECT content, embedding <-> %s::vector AS distance
        FROM documents
        ORDER BY distance
        LIMIT %s
    """, (query_embedding, top_k))

    return cur.fetchall()
```

---

### 📐 계층 구조 매핑 (권장 아키텍처)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        권장 계층 구조                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐                                                        │
│  │   ROUTER    │  routes/mcp_router.py                                  │
│  │             │  • 인증/권한/레이트리밋                                 │
│  │             │  • 입력 스키마 검증                                     │
│  │             │  • 어떤 Controller로 보낼지 라우팅                      │
│  └──────┬──────┘                                                        │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              CONTROLLER = KoELECTRA 게이트                       │    │
│  │              ochestrator/mcp_ochestrator/mcp_controller.py       │    │
│  │                                                                  │    │
│  │  • KoELECTRA로 "EXAONE을 호출할지 말지" 판정                     │    │
│  │  • 워크플로 제어 (재시도/타임아웃/분기/관찰가능성)                │    │
│  │  • 세션 상태 관리                                                │    │
│  │  • ❌ 생성형 결과를 만들지 않음 (판정/라우팅만)                   │    │
│  │                                                                  │    │
│  │  Short-circuit:                                                  │    │
│  │    spam_prob < 0.3 → 즉시 ALLOW 🚀                               │    │
│  │    spam_prob > 0.8 → 즉시 DENY 🚀                                │    │
│  │    0.3~0.8 → 에스컬레이션 🔄                                     │    │
│  └──────────────────────────┬──────────────────────────────────────┘    │
│                             │ (필요시에만)                              │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              SERVICE = EXAONE 정밀 판독/생성                     │    │
│  │              domain/spam_classifier/services/exaone_hub.py       │    │
│  │                                                                  │    │
│  │  • 정밀 판독 (근거 요약, 이유 생성)                              │    │
│  │  • 최종 분류/판별 (스팸 여부/카테고리/리스크)                    │    │
│  │  • 사용자 메시지 생성 (설명/조치 제안)                           │    │
│  │  • ✅ EXAONE은 항상 호출하지 않고, 필요할 때만 호출              │    │
│  └──────────────────────────┬──────────────────────────────────────┘    │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              REPOSITORY = 지식 창고                              │    │
│  │              domain/*/repository/                                │    │
│  │                                                                  │    │
│  │  • 원문/메타 저장, 분류 결과, 피처                               │    │
│  │  • 실행 로그, 어댑터 버전, 캐시                                  │    │
│  │  • RAG: 벡터 인덱스/문서 스토어 (pgvector)                       │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              ONTOLOGY = 공통 기준 레이어 (SSOT)                   │    │
│  │              domain/spam_classifier/services/ontology.py         │    │
│  │                                                                  │    │
│  │  • 용어/개념/관계/규칙/매핑                                      │    │
│  │  • Controller: "라우팅 힌트/정규화" 용도로 가볍게 참조           │    │
│  │  • Service: "정밀 해석/설명"에 깊게 참조                         │    │
│  │  • ⚠️ 맨 마지막 단계가 아닌 "전 계층이 참조하는 기준"            │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 📊 용어 관계도 (전체 시스템 뷰)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ORCHESTRATOR                                    │
│                    (생애주기 관리자 - 최상위 개체)                           │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                    LangGraph StateGraph                           │     │
│   │                                                                   │     │
│   │  ┌─────────────┐                                                  │     │
│   │  │  GATEWAY    │  ← KoELECTRA (수문장)                            │     │
│   │  │  (입구)     │                                                  │     │
│   │  └──────┬──────┘                                                  │     │
│   │         │                                                         │     │
│   │         ▼                                                         │     │
│   │  ┌─────────────────────────────────────────────────────────┐      │     │
│   │  │              BRANCH NODES (전문가 군집)                  │      │     │
│   │  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │      │     │
│   │  │  │SPAM  │ │SENTI │ │SUMM  │ │CLASS │ │NOTI  │          │      │     │
│   │  │  │FILTER│ │MENT  │ │ARY   │ │      │ │FIER  │          │      │     │
│   │  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘          │      │     │
│   │  └─────┼────────┼────────┼────────┼────────┼───────────────┘      │     │
│   │        └────────┴────────┼────────┴────────┘                      │     │
│   │                          ▼                                        │     │
│   │                 ┌─────────────────┐                               │     │
│   │                 │   STAR NODE     │  ← EXAONE Hub (핵심 두뇌)     │     │
│   │                 │ (중앙 지능 허브) │                               │     │
│   │                 └─────────────────┘                               │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                      REPOSITORY (지식 창고)                       │     │
│   │  ┌──────────────────┐    ┌──────────────────┐                     │     │
│   │  │ AgentRepository  │    │   Vector DB      │                     │     │
│   │  │ (브랜치 관리)    │    │   (pgvector)     │                     │     │
│   │  └──────────────────┘    └──────────────────┘                     │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                    LoRA ADAPTERS (전문 스킬)                       │     │
│   │  ┌─────────────────┐    ┌─────────────────┐                       │     │
│   │  │ EXAONE Adapter  │    │ KoELECTRA LoRA  │                       │     │
│   │  │ (스팸 판단)     │    │ (스팸/콜센터)   │                       │     │
│   │  └─────────────────┘    └─────────────────┘                       │     │
│   └───────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌟 Star Topology 아키텍처

### 개념도

```
                    ┌─────────────────────────────────┐
                    │         GATEWAY NODE            │
                    │    (KoELECTRA 1st Filter)       │
                    └───────────────┬─────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
         ┌────────┐           ┌─────────┐           ┌─────────┐
         │  DENY  │           │ ALLOW   │           │  ROUTE  │
         │  (END) │           │         │           │         │
         └────────┘           └────┬────┘           └────┬────┘
                                   │                     │
                                   │         ┌───────────┴───────────┐
                                   │         │    BRANCH ROUTER      │
                                   │         └───────────┬───────────┘
                                   │                     │
              ┌────────────────────┼─────────────────────┼────────────────────┐
              │                    │                     │                    │
              ▼                    ▼                     ▼                    ▼
        ┌──────────┐        ┌──────────┐          ┌──────────┐        ┌──────────┐
        │  SPAM    │        │SENTIMENT │          │ SUMMARY  │        │  CLASS   │
        │ FILTER   │        │ ANALYSIS │          │          │        │ IFICATION│
        └────┬─────┘        └────┬─────┘          └────┬─────┘        └────┬─────┘
             │                   │                     │                   │
             └───────────────────┴──────────┬──────────┴───────────────────┘
                                            │
                                            ▼
                              ┌─────────────────────────────┐
                              │      EXAONE STAR HUB        │
                              │    (Central Intelligence)   │
                              │                             │
                              │  • 유문작업 (Output Refine) │
                              │  • 다음 브랜치 결정         │
                              │  • 순환 제어                │
                              └─────────────┬───────────────┘
                                            │
                              ┌─────────────┴───────────────┐
                              │                             │
                              ▼                             ▼
                      ┌─────────────┐              ┌─────────────┐
                      │  MORE WORK  │              │    END      │
                      │  (Loop Back)│              │  (Complete) │
                      └─────────────┘              └─────────────┘
```

### 흐름 설명

1. **Gateway Node**: KoELECTRA로 빠른 1차 필터링
   - `spam_prob < 0.3`: 즉시 **ALLOW**
   - `spam_prob > 0.8`: 즉시 **DENY**
   - `0.3 ≤ spam_prob ≤ 0.8`: EXAONE LLM으로 정책 결정

2. **Branch Router**: 정책에 따라 적절한 브랜치 선택
   - `spam_filter`: 스팸 상세 분석
   - `sentiment`: 감정 분석
   - `summary`: 텍스트 요약
   - `classification`: 텍스트 분류
   - `notification`: 알림 처리

3. **EXAONE Star Hub**: 중앙 허브 (Star Topology의 핵심)
   - **유문작업**: 브랜치 결과를 자연스러운 문장으로 정제
   - **다음 브랜치 결정**: 추가 분석이 필요한지 판단
   - **순환 제어**: 다른 브랜치로 재라우팅 가능

---

## 🧠 모델 구성

### KoELECTRA (1차 필터)

| 항목 | 값 |
|------|-----|
| Base Model | `monologg/koelectra-small-v3-discriminator` |
| Task | Sequence Classification |
| Fine-tuning | LoRA (rank=8, alpha=16) |
| 용도 | 빠른 스팸 확률 계산 |

### EXAONE 3.5B (2차 판단)

| 항목 | 값 |
|------|-----|
| Model | `LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct` |
| Task | Causal Language Modeling |
| Fine-tuning | LoRA Adapter |
| 용도 | 정밀 판단 + 유문작업 |

### 모델 경로

```python
# config.py
KOELECTRA_MODEL_PATH = "./backend/models/koelectra/spam-lora"
KOELECTRA_BASE_MODEL = "monologg/koelectra-small-v3-discriminator"
EXAONE_MODEL_PATH = "./backend/models/exaone/exaone_model"
```

---

## 🔌 API 엔드포인트

### MCP Gateway API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/mcp/gateway` | 스팸 필터 게이트웨이 |
| GET | `/api/mcp/gateway/session/{session_id}` | 세션 히스토리 조회 |
| DELETE | `/api/mcp/gateway/session/{session_id}` | 세션 삭제 |
| GET | `/api/mcp/health` | MCP 헬스체크 |

### Chat API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/chat` | RAG 기반 채팅 |

### Request/Response 예시

```json
// POST /api/mcp/gateway
// Request
{
  "text": "긴급! 당첨되셨습니다. 지금 바로 확인하세요!",
  "session_id": "session_123",
  "request_id": "req_001"
}

// Response
{
  "request_id": "req_001",
  "session_id": "session_123",
  "spam_prob": 0.95,
  "label": "spam",
  "confidence": "high",
  "gateway_action": "quarantine",
  "gateway_message": "요청이 거부되었습니다. (이유: KOELECTRA_HIGH_SPAM)",
  "exaone_used": true,
  "exaone_result": {
    "action": "deny",
    "final_output": "스팸으로 판정된 메시지입니다.",
    "branch_results": [...]
  }
}
```

---

## 🎯 온톨로지 정책

### AgentBranch (브랜치 타입)

```python
class AgentBranch(str, Enum):
    SPAM_FILTER = "spam_filter"      # 스팸 필터
    SENTIMENT = "sentiment"          # 감정 분석
    SUMMARY = "summary"              # 요약
    CLASSIFICATION = "classification" # 텍스트 분류
    NOTIFICATION = "notification"    # 알림
```

### ActionType (게이트웨이 액션)

```python
class ActionType(str, Enum):
    ALLOW = "allow"           # 허용
    DENY = "deny"             # 거부
    ROUTE = "route"           # 브랜치로 라우팅
    QUARANTINE = "quarantine" # 격리
    ASK_USER = "ask_user"     # 사용자 확인 요청
```

### 기본 라우팅 규칙

| 우선순위 | 조건 | 액션 | 설명 |
|---------|------|------|------|
| 100 | 긴급/당첨/보상 키워드 | DENY | 즉시 차단 |
| 95 | URL 포함 | QUARANTINE | 격리 (검증 필요) |
| 80 | 불만/불편 키워드 | ROUTE → sentiment | 감정 분석 |
| 70 | 500자 이상 | ROUTE → summary | 요약 필요 |
| 50 | 기본 | ROUTE → spam_filter | 스팸 체크 |

---

## 🔄 데이터 흐름 (Controller-Gate Pattern)

```
[Client Request]
       │
       ▼
┌──────────────────┐
│   mcp_router.py  │  ← Router: 인증/검증/라우팅
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│              McpController (게이트/에스컬레이션)          │
│                                                          │
│  ┌──────────────┐                                        │
│  │  KoELECTRA   │  ← 1차 게이트 판정                     │
│  └──────┬───────┘                                        │
│         │                                                │
│         ├─→ spam_prob < 0.3 ─→ 🚀 즉시 ALLOW ──────────┐ │
│         │                                              │ │
│         ├─→ spam_prob > 0.8 ─→ 🚀 즉시 DENY ───────────┤ │
│         │                                              │ │
│         └─→ 0.3 ~ 0.8 ─→ 🔄 에스컬레이션               │ │
│                              │                         │ │
└──────────────────────────────┼─────────────────────────┼─┘
                               │                         │
                               ▼                         │
                    ┌──────────────────┐                 │
                    │  McpOrchestrator │                 │
                    └────────┬─────────┘                 │
                             │                           │
                             ▼                           │
                    ┌──────────────────┐                 │
                    │ star_mcp_graph   │                 │
                    │  (StateGraph)    │                 │
                    └────────┬─────────┘                 │
                             │                           │
                             ▼                           │
                    ┌──────────────────┐                 │
                    │  EXAONE Service  │                 │
                    │  (정밀 판독/생성) │                 │
                    └────────┬─────────┘                 │
                             │                           │
                             ▼                           ▼
                    ┌──────────────────────────────────────┐
                    │           [Response]                 │
                    └──────────────────────────────────────┘
```

**핵심 포인트:**
- **Controller 레벨**: KoELECTRA 게이트 판정 (에스컬레이션 여부 결정)
- **Short-circuit**: 명확한 케이스는 EXAONE 호출 없이 즉시 응답
- **Service 레벨**: EXAONE은 애매한 케이스에만 호출 (정밀 판독/생성/최종 판단)

---

## 📦 의존성

### 핵심 프레임워크

| 패키지 | 버전 | 용도 |
|--------|------|------|
| fastapi | ^0.100.0 | Web Framework |
| uvicorn | ^0.22.0 | ASGI Server |
| langgraph | ^0.2.0 | State Graph |
| langchain | ^0.3.0 | LLM Orchestration |

### ML/AI 라이브러리

| 패키지 | 버전 | 용도 |
|--------|------|------|
| transformers | ^4.40.0 | Model Loading |
| torch | ^2.0.0 | Deep Learning |
| peft | ^0.10.0 | LoRA Fine-tuning |
| sentence-transformers | ^2.0.0 | Embeddings |

### 데이터베이스

| 패키지 | 버전 | 용도 |
|--------|------|------|
| psycopg2-binary | ^2.9.0 | PostgreSQL |
| pgvector | ^0.2.0 | Vector Search |

---

## 🚀 실행 방법

### 서버 실행

```bash
# FastAPI 서버 모드
python -m backend.main --server

# CLI 데모 모드
python -m backend.main
```

### Docker 실행

```bash
docker-compose up -d backend
```

### 환경 변수

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/db
OPENAI_API_KEY=sk-...
KOELECTRA_MODEL_PATH=./backend/models/koelectra/spam-lora
```

---

## 🧪 테스트

```bash
# 컴포넌트 테스트
python backend/test_mcp_components.py

# Star MCP 통합 테스트
python backend/test_star_mcp.py

# 간단한 테스트
python backend/test_star_mcp_simple.py
```

---

## 📝 설계 결정 사항

### 1. Star Topology 선택 이유

- **중앙 집중식 제어**: EXAONE 허브가 모든 브랜치 결과를 종합
- **유연한 라우팅**: 동적으로 다음 브랜치 결정 가능
- **순환 구조 지원**: 필요시 여러 브랜치를 순차적으로 실행

### 2. Two-Stage Filtering

- **KoELECTRA (1단계)**: 빠른 필터링 (~10ms)
- **EXAONE (2단계)**: 정밀 판단 (~500ms)
- **효율성**: 명확한 케이스는 1단계에서 즉시 처리

### 3. Vertical Slicing

- **독립성**: 각 도메인은 독립적으로 테스트/배포 가능
- **확장성**: 새 도메인 추가 시 기존 코드 영향 최소화
- **유지보수성**: 도메인별 책임 분리

---

## 🔮 향후 계획

- [ ] ESG 분석 도메인 추가
- [ ] 멀티모달 (이미지) 지원
- [ ] A/B 테스트 프레임워크
- [ ] 모델 버전 관리 시스템
- [ ] 분산 처리 (Ray/Dask)

---

*Last Updated: 2026-01-19*

