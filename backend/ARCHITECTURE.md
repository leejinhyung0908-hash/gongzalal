# 🏗️ Backend Architecture

> **공잘알 (공무원 시험, 잘 알려주는 AI)** 백엔드 시스템 구조 문서

---

## 📁 디렉토리 구조

```
backend/
├── main.py                          # FastAPI 앱 진입점, 라이프사이클, 라우터 등록
├── config.py                        # 환경 변수 기반 설정 (Settings 클래스)
├── dependencies.py                  # DI: DB 연결, LLM 로드, QLoRA 서비스
├── requirements.txt                 # Python 패키지 의존성
│
├── api/                             # 🌐 API 계층 (라우터)
│   └── v1/
│       ├── admin/                   # Admin 라우터 (도메인별 REST 엔드포인트)
│       │   ├── chat_router.py       #   /api/chat — 종합 채팅 엔드포인트
│       │   ├── exam_router.py       #   /api/v1/admin/exam
│       │   ├── question_router.py   #   /api/v1/admin/questions
│       │   ├── commentary_router.py #   /api/v1/admin/commentaries
│       │   ├── user_router.py       #   /api/v1/admin/users
│       │   ├── solving_log_router.py        # /api/v1/admin/solving-logs
│       │   ├── study_plan_router.py         # /api/v1/admin/study-plans
│       │   ├── mentoring_knowledge_router.py # /api/v1/admin/mentoring-knowledge
│       │   ├── audio_note_router.py         # /api/v1/admin/audio-notes
│       │   └── mcp_router.py               # /api/v1/admin/mcp
│       └── shared/
│           └── redis.py             # Upstash Redis: JWT, BullMQ, 대화 이력 관리
│
├── core/                            # ⚙️ 핵심 인프라
│   ├── database/                    # SQLAlchemy 기반 DB 유틸
│   │   ├── base.py                  #   Base 모델 선언
│   │   ├── mixin.py                 #   TimestampMixin (created_at, updated_at)
│   │   ├── session.py               #   세션 팩토리
│   │   └── alembic_utils.py         #   Alembic 마이그레이션 유틸
│   ├── llm/                         # LLM 관리 시스템
│   │   ├── base.py                  #   BaseLLM 추상 클래스
│   │   ├── registry.py              #   ModelRegistry (모델 타입 등록)
│   │   ├── factory.py               #   LLMFactory (팩토리 패턴)
│   │   ├── loader.py                #   ModelLoader (모델 로드/캐싱)
│   │   ├── register_models.py       #   서버 시작 시 모델 타입 등록
│   │   └── providers/
│   │       ├── exaone_llm.py        #   EXAONE 3.5 2.4B (메인 LLM)
│   │       └── midm_llm.py          #   Mi:dm (레거시)
│   ├── utils/
│   │   ├── embedding.py             #   KURE-v1 임베딩 (1024차원)
│   │   └── database.py              #   pgvector 유사도 검색
│   └── workers/
│       └── embedding_worker.py      #   BullMQ 임베딩 백그라운드 워커
│
├── domain/                          # 🏢 도메인 계층
│   ├── shared/                      # 공유 베이스
│   │   ├── bases/                   #   공통 Base 클래스
│   │   ├── models/
│   │   │   ├── states/
│   │   │   │   └── base_state.py    #   BaseProcessingState (LangGraph용)
│   │   │   └── enums/
│   │   │       └── strategy_type.py #   전략 타입 열거
│   │   ├── repositories/            #   공통 Repository 인터페이스
│   │   └── services/                #   공통 Service 인터페이스
│   │
│   └── admin/                       # Admin 도메인 (메인)
│       ├── models/
│       │   ├── bases/               # 📊 SQLAlchemy ORM 모델 (9개 테이블)
│       │   │   ├── exam.py          #   시험 (exams)
│       │   │   ├── question.py      #   문제 (questions)
│       │   │   ├── question_image.py #  문제 이미지 (question_images)
│       │   │   ├── commentary.py    #   해설 (commentaries)
│       │   │   ├── user.py          #   사용자 (users)
│       │   │   ├── user_solving_log.py # 풀이 기록 (user_solving_logs)
│       │   │   ├── study_plan.py    #   학습 계획 (study_plans)
│       │   │   ├── mentoring_knowledge.py # 합격 수기 (mentoring_knowledge)
│       │   │   └── audio_note.py    #   오디오 노트 (audio_notes)
│       │   ├── states/              # LangGraph 상태 스키마
│       │   │   ├── chat_state.py    #   ChatProcessingState (멀티턴 포함)
│       │   │   ├── exam_state.py    #   ExamProcessingState
│       │   │   ├── commentary_state.py
│       │   │   └── user_state.py
│       │   ├── transfers/           # Pydantic DTO (Request/Response)
│       │   │   ├── chat_model.py    #   ChatRequest, ChatResponse
│       │   │   ├── exam_transfer.py #   ExamUploadRequest 등
│       │   │   ├── question_transfer.py
│       │   │   ├── commentary_transfer.py
│       │   │   └── user_transfer.py
│       │   └── enums/
│       │
│       ├── hub/                     # 🎯 Hub (오케스트레이터, MCP)
│       │   ├── orchestrators/       # LangGraph StateGraph 기반 Flow
│       │   │   ├── chat_flow.py     #   ★ 종합 라우터 (멀티턴 대화 포함)
│       │   │   ├── exam_flow.py     #   시험/정답 조회 Flow
│       │   │   ├── question_flow.py #   문제 관리 Flow
│       │   │   ├── study_plan_flow.py #  학습 계획 생성 Flow (분석+RAG+EXAONE)
│       │   │   ├── solving_log_flow.py # 풀이 기록 Flow
│       │   │   ├── commentary_flow.py #  해설 Flow
│       │   │   ├── audio_note_flow.py #  오디오 노트 Flow
│       │   │   ├── user_flow.py     #   사용자 관리 Flow
│       │   │   └── mcp_controller.py #  MCP 컨트롤러
│       │   ├── mcp/                 # MCP (Model Context Protocol) 서버
│       │   │   └── central_mcp_server.py # KoELECTRA + EXAONE 중앙 관리
│       │   └── repositories/        # 데이터 접근 계층
│       │       ├── exam_repository.py
│       │       ├── commentary_repository.py
│       │       ├── user_repository.py
│       │       ├── solving_log_repository.py
│       │       ├── study_plan_repository.py
│       │       └── audio_note_repository.py
│       │
│       └── spokes/                  # 🔧 Spokes (에이전트, 서비스)
│           ├── agents/
│           │   ├── retrieval/       # 검색/RAG 에이전트
│           │   │   ├── rag_agent.py         # 기본 RAG (rag_answer, rag_with_llm 등)
│           │   │   ├── mentoring_rag.py     # ★ 멘토링 RAG (합격 수기 검색 + EXAONE)
│           │   │   └── query_rewriter.py    # ★ 멀티턴 쿼리 재구성 (규칙/EXAONE)
│           │   ├── analysis/        # 분석 에이전트
│           │   │   ├── entity_extractor.py  # 엔티티 추출
│           │   │   ├── solving_log_analyzer.py # 풀이 분석 (약점/강점/추세)
│           │   │   └── study_plan_prompt_builder.py # 학습 계획 프롬프트 빌더
│           │   ├── conversation/    # 대화 에이전트
│           │   │   └── chat_agent.py
│           │   ├── exam_agent.py    # 시험 에이전트
│           │   ├── commentary_agent.py
│           │   └── user_agent.py
│           └── services/            # 비즈니스 서비스
│               ├── exam_service.py
│               ├── commentary_service.py
│               ├── user_service.py
│               ├── solving_log_service.py
│               ├── study_plan_service.py
│               ├── question_image_service.py
│               ├── audio_note_service.py
│               └── success_stories_rag.py   # 합격 수기 RAG 서비스
│
└── tools/                           # 🛠️ 오프라인 유틸리티 스크립트
    ├── crawl_success_stories.py     #   합격 수기 크롤링
    ├── build_exam_dataset.py        #   시험 데이터셋 빌드
    ├── train_gateway_classifier.py  #   KoELECTRA 게이트웨이 분류기 학습
    └── ...                          #   기타 데이터 전처리/학습 도구
```

---

## 🔄 서비스 흐름 (Service Flow)

### 1. 서버 시작 (Lifespan)

```
main.py → lifespan()
├── 1) connect_db()           → Neon PostgreSQL 연결 (psycopg3)
├── 2) setup_schema()         → pgvector 어댑터 등록
├── 3) run_alembic_upgrade()  → DB 마이그레이션 자동 적용
├── 4) register_all_models()  → LLM 레지스트리 등록 (exaone, midm)
├── 5) get_central_mcp_server() → MCP 서버 초기화
└── 6) setup_redis()          → Upstash Redis 연결 + 임베딩 워커 시작
```

### 2. 채팅 요청 처리 (메인 파이프라인)

```
[프론트엔드] POST /api/chat { question, mode, thread_id }
        │
        ▼
┌─ chat_router.py ─────────────────────────────────────┐
│  1. request 검증                                       │
│  2. EXAONE LLM 로드 (get_llm → ModelLoader → ExaoneLLM)│
│  3. ChatFlow.process_chat_request() 호출                │
└──────────────────────────┬───────────────────────────┘
                           ▼
┌─ ChatFlow (LangGraph StateGraph) ────────────────────┐
│                                                       │
│  START                                                │
│    │                                                  │
│    ▼                                                  │
│  [validate] ─── 입력 검증                              │
│    │                                                  │
│    ▼                                                  │
│  [load_history] ─── Redis에서 대화 이력 로드 (thread_id)  │
│    │                chat_history, context_summary 설정  │
│    ▼                                                  │
│  [rewrite_query] ── EXAONE으로 검색 쿼리 재구성          │
│    │                (대화 맥락 반영, 폴백: 규칙 기반)     │
│    ▼                                                  │
│  [classify_request] ── 키워드 기반 요청 분류              │
│    │                                                  │
│    ├── "exam"       → [route_exam]       → ExamFlow   │
│    ├── "question"   → [route_question]   → QuestionFlow│
│    ├── "study_plan" → [route_study_plan] → StudyPlanFlow│
│    ├── "solving_log"→ [route_solving_log]→ SolvingLogFlow│
│    ├── "mentoring"  → [route_mentoring]  → MentoringRAG│
│    ├── "audio_note" → [route_audio_note] → AudioNoteFlow│
│    └── "chat"       → [route_chat]       → RAG 폴백    │
│    │                                                  │
│    ▼                                                  │
│  [save_history] ─── Redis에 질문+답변 저장              │
│    │                context_summary 자동 갱신           │
│    ▼                                                  │
│  [finalize] ─── 결과 정리                              │
│    │                                                  │
│  END                                                  │
└───────────────────────────────────────────────────────┘
```

### 3. 멘토링 RAG 파이프라인 (route_mentoring)

```
사용자 질문 (재구성된 쿼리)
        │
        ▼
┌─ mentoring_rag.py ───────────────────────────────────┐
│                                                       │
│  1. KURE-v1 임베딩                                     │
│     query → generate_embedding() → [1024차원 벡터]     │
│                                                       │
│  2. pgvector 코사인 유사도 검색                          │
│     mentoring_knowledge 테이블에서 top-K 검색            │
│     (4,910건 합격 수기 데이터)                            │
│                                                       │
│  3. 프롬프트 구성 (멀티턴 컨텍스트 포함)                   │
│     ┌──────────────────────────────────┐              │
│     │ [시스템 역할] 멘토 페르소나        │              │
│     │ [이전 대화 요약] context_summary   │              │
│     │ [이전 대화 이력] 최근 3턴          │              │
│     │ [합격 수기 참고] top-K 검색 결과   │              │
│     │ [현재 질문] 사용자 원래 질문        │              │
│     └──────────────────────────────────┘              │
│                                                       │
│  4. EXAONE 답변 생성                                    │
│     llm.generate(prompt, max_tokens=1024)              │
│     (실패 시 raw 포맷팅으로 폴백)                         │
│                                                       │
└───────────────────────────────────────────────────────┘
```

### 4. 학습 계획 생성 파이프라인 (route_study_plan)

```
사용자 요청: "학습 계획 짜줘"
        │
        ▼
┌─ study_plan_flow.py ─────────────────────────────────┐
│                                                       │
│  Step 1: 풀이 로그 분석 (SolvingLogAnalyzer)            │
│    → 과목별 정답률, 약점/강점, 점수 추세, 오류 분포       │
│                                                       │
│  Step 2: RAG 쿼리 생성 + 검색                           │
│    → 분석 결과 기반 검색 쿼리 → mentoring_knowledge 검색  │
│                                                       │
│  Step 3: 사용자 프로필 조회                              │
│                                                       │
│  Step 4: EXAONE 학습 계획 생성 (StudyPlanPromptBuilder) │
│    → 분석 결과 + RAG 컨텍스트 + 사용자 정보 → 프롬프트   │
│    → EXAONE 생성 (실패 시 템플릿 폴백)                   │
│                                                       │
│  Step 5: study_plans 테이블에 저장                      │
│                                                       │
└───────────────────────────────────────────────────────┘
```

---

## 🧩 핵심 컴포넌트

### LLM 시스템

```
                    ┌─────────────┐
                    │  BaseLLM    │ (추상 클래스)
                    │  load()     │
                    │  generate() │
                    │  unload()   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼                         ▼
     ┌──────────────┐          ┌──────────────┐
     │  ExaoneLLM   │          │   MidmLLM    │
     │  (메인 LLM)  │          │  (레거시)    │
     │  2.4B 4bit   │          │              │
     └──────────────┘          └──────────────┘

ModelRegistry ← register_all_models() 에서 등록
     ↓
LLMFactory.create(model_type) → BaseLLM 인스턴스
     ↓
ModelLoader.load_model() → 캐싱 + 반환
```

### 임베딩 시스템

```
KURE-v1 (nlpai-lab/KURE-v1)
├── 한국어 특화 SentenceTransformer
├── 출력 차원: 1024
├── generate_embedding(text) → [float x 1024]
├── generate_embeddings_batch(texts) → [[float x 1024], ...]
└── lazy loading (최초 호출 시 1회 로드)
```

### 데이터베이스 (Neon PostgreSQL + pgvector)

| 테이블 | 설명 | 벡터 컬럼 |
|--------|------|-----------|
| `exams` | 시험 정보 | `exam_vector(1024)` |
| `questions` | 문제 | `question_vector(1024)` |
| `question_images` | 문제 이미지 | `image_vector(1024)` |
| `commentaries` | 해설 | `commentary_vector(1024)` |
| `users` | 사용자 | `user_vector(1024)` |
| `user_solving_logs` | 풀이 기록 | `solving_vector(1024)` |
| `study_plans` | 학습 계획 | `plan_vector(1024)` |
| `mentoring_knowledge` | 합격 수기 (4,910건) | `knowledge_vector(1024)` |
| `audio_notes` | 오디오 노트 | `audio_vector(1024)` |

### 세션 관리 (Upstash Redis)

```
chat:session:{thread_id}        ← 대화 이력 (TTL 30분)
├── messages: [{role, text, timestamp}, ...]
└── context_summary: "노베이스, 1년, 일반행정직"

jwt:access_token:{token}        ← JWT 토큰
jwt:user:{user_id}              ← 사용자별 토큰 매핑
bull:{queue}:wait               ← BullMQ 작업 큐
```

---

## 🌐 API 엔드포인트 맵

| Method | Path | Router | 설명 |
|--------|------|--------|------|
| POST | `/api/chat` | chat_router | 종합 채팅 (멀티턴 대화) |
| POST | `/api/chat/qlora` | chat_router | QLoRA 모델 채팅 |
| GET/POST | `/api/v1/admin/exam/*` | exam_router | 시험 CRUD + JSONL 업로드 |
| GET/POST | `/api/v1/admin/questions/*` | question_router | 문제 CRUD |
| GET/POST | `/api/v1/admin/commentaries/*` | commentary_router | 해설 CRUD |
| GET/POST | `/api/v1/admin/users/*` | user_router | 사용자 관리 |
| GET/POST | `/api/v1/admin/solving-logs/*` | solving_log_router | 풀이 기록 |
| GET/POST | `/api/v1/admin/study-plans/*` | study_plan_router | 학습 계획 + 분석 |
| GET/POST | `/api/v1/admin/mentoring-knowledge/*` | mentoring_knowledge_router | 합격 수기 + 임베딩 |
| GET/POST | `/api/v1/admin/mcp/*` | mcp_router | MCP 서버 제어 |

---

## 🔀 멀티턴 대화 흐름 (상세)

```
[1번째 질문] "나 노베이스 1년 일행직 준비하려고 해"

  Frontend: threadIdRef = "sess_abc123"
       │
       ▼ POST /api/chat { question, mode: "rag_local", thread_id: "sess_abc123" }
       │
  load_history → Redis에 없음 → chat_history = []
  rewrite_query → 이력 없음 → 원래 질문 그대로
  classify → "mentoring"
  route_mentoring → KURE-v1 임베딩 → pgvector 검색 → EXAONE 답변
  save_history → Redis에 저장:
      chat:session:sess_abc123 = {
          messages: [
              {role:"user", text:"나 노베이스 1년 일행직 준비하려고 해"},
              {role:"bot",  text:"노베이스 1년 일반행정직 준비 전략은..."}
          ],
          context_summary: "노베이스, 1년, 일행직, 일반행정"
      }

─────────────────────────────────────────────────────

[2번째 질문] "학습 계획 짜줘"

  load_history → Redis에서 이전 대화 로드
      chat_history: [{user: "나 노베이스..."}, {bot: "노베이스 1년..."}]
      context_summary: "노베이스, 1년, 일행직, 일반행정"

  rewrite_query (EXAONE 기반):
      입력: "학습 계획 짜줘" + context_summary + chat_history
      출력: "노베이스 1년 9급 일반행정직 단기 합격 학습 계획 및 과목별 커리큘럼 추천"

  classify → "study_plan"
  route_study_plan → 재구성된 쿼리로 RAG 검색 → 풀이 분석 → EXAONE 계획 생성

  save_history → Redis 갱신 (messages 추가, context_summary 업데이트)
```

---

## 📦 기술 스택 요약

| 구성 요소 | 기술 |
|-----------|------|
| **웹 프레임워크** | FastAPI + Uvicorn |
| **LLM** | EXAONE 3.5 2.4B (4-bit 양자화, 로컬) |
| **임베딩** | KURE-v1 (1024차원, SentenceTransformer) |
| **벡터 DB** | Neon PostgreSQL + pgvector |
| **오케스트레이터** | LangGraph StateGraph |
| **캐시/세션** | Upstash Redis (대화 이력, JWT, BullMQ) |
| **DB 어댑터** | psycopg3 (동기), asyncpg (LangChain용) |
| **ORM** | SQLAlchemy 2.0 (Mapped + mapped_column) |
| **마이그레이션** | Alembic (자동 적용) |
| **데이터 검증** | Pydantic v2 |
| **MCP** | FastMCP (KoELECTRA + EXAONE 통합) |

---

## 🏛️ 아키텍처 패턴

### Hub-and-Spoke 패턴

```
         ┌──────────────────┐
         │   chat_router    │ ← API 진입점
         └────────┬─────────┘
                  │
         ┌────────▼─────────┐
         │    ChatFlow       │ ← Hub (종합 오케스트레이터)
         │  (LangGraph)      │
         └────────┬─────────┘
                  │
    ┌─────────────┼─────────────┬────────────┐
    ▼             ▼             ▼            ▼
┌────────┐  ┌─────────┐  ┌──────────┐  ┌─────────┐
│ExamFlow│  │Mentoring│  │StudyPlan │  │  기타   │  ← Spokes
│        │  │  RAG    │  │  Flow    │  │  Flows  │
└───┬────┘  └────┬────┘  └────┬─────┘  └────┬────┘
    │            │            │              │
    ▼            ▼            ▼              ▼
┌─────────────────────────────────────────────────┐
│         Neon PostgreSQL + pgvector               │
│         (9개 테이블, KURE-v1 임베딩)               │
└─────────────────────────────────────────────────┘
```

### 의존성 주입 (DI)

```python
# dependencies.py
get_db_connection()  → psycopg.Connection  (전역 싱글톤)
get_llm()            → BaseLLM             (ModelLoader 캐싱)
get_qlora_service()  → QLoRAChatService    (전역 싱글톤)
get_pg_engine()      → PGEngine            (LangChain 비동기)
```

### LLM 로드 체인

```
get_llm(model_name, model_type)
  → ModelLoader.load_model()
    → LLMFactory.create()
      → ModelRegistry.get(model_type)
        → ExaoneLLM(model_path)
          → llm.load() → HuggingFace transformers 4-bit 로드
```

