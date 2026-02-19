# Backend 구조 문서

## 📁 디렉토리 구조

```
backend/
├── api/                    # API 라우터 레이어
│   └── v1/
│       └── admin/          # 관리자 API
│           ├── chat_router.py          # 채팅 API
│           ├── exam_router.py          # 시험 정답 조회 API
│           ├── mcp_router.py           # MCP 게이트웨이 API
│           ├── user_router.py          # 사용자 관리 API
│           ├── commentary_router.py    # 해설 관리 API
│           └── email_router.py        # 이메일 API
│
├── core/                   # 핵심 유틸리티 및 LLM 관리
│   ├── llm/                # LLM 모델 관리
│   │   ├── base.py                    # BaseLLM 추상 클래스
│   │   ├── factory.py                 # LLM 팩토리 패턴
│   │   ├── loader.py                  # 모델 로더
│   │   ├── registry.py                # 모델 레지스트리
│   │   ├── register_models.py         # 모델 등록
│   │   └── providers/                 # LLM 프로바이더
│   │       ├── base_adapter.py
│   │       ├── exaone_llm.py          # EXAONE 모델
│   │       ├── midm_llm.py            # Mi:dm 모델
│   │       ├── spam_filter_adapter.py # 스팸 필터 어댑터
│   │       ├── sentiment_adapter.py    # 감정 분석 어댑터
│   │       ├── summary_adapter.py     # 요약 어댑터
│   │       ├── classification_adapter.py
│   │       └── notification_adapter.py
│   └── utils/              # 공통 유틸리티
│       ├── database.py      # 데이터베이스 유틸리티
│       └── embedding.py     # 임베딩 유틸리티
│
├── domain/                 # 도메인 로직 (DDD 패턴)
│   └── admin/              # 관리자 도메인
│       ├── agents/         # 에이전트 (정책 기반 처리)
│       │   ├── exam_agent.py           # 시험 정답 조회 에이전트
│       │   ├── commentary_agent.py    # 해설 생성 에이전트
│       │   ├── user_agent.py           # 사용자 관리 에이전트
│       │   ├── conversation/
│       │   │   └── chat_agent.py       # 채팅 에이전트
│       │   ├── retrieval/
│       │   │   └── rag_agent.py        # RAG 에이전트
│       │   └── analysis/
│       │       ├── spam_detector.py    # KoELECTRA 스팸 감지
│       │       └── verdict_agent.py   # EXAONE 판별기
│       │
│       ├── services/       # 서비스 (규칙 기반 처리)
│       │   ├── exam_service.py        # 시험 정답 조회 서비스
│       │   ├── commentary_service.py  # 해설 관리 서비스
│       │   └── user_service.py        # 사용자 관리 서비스
│       │
│       ├── orchestrators/  # 오케스트레이터 (분기 처리)
│       │   ├── exam_flow.py           # 시험 요청 처리 플로우
│       │   ├── commentary_flow.py      # 해설 요청 처리 플로우
│       │   ├── user_flow.py           # 사용자 요청 처리 플로우
│       │   └── mcp_controller.py      # MCP 게이트웨이 컨트롤러
│       │
│       ├── models/         # 도메인 모델 (Pydantic)
│       │   ├── base_model.py          # 기본 요청/응답 모델
│       │   ├── chat_model.py          # 채팅 모델
│       │   ├── exam_model.py          # 시험 모델
│       │   ├── commentary_model.py   # 해설 모델
│       │   ├── user_model.py         # 사용자 모델
│       │   ├── email_model.py        # 이메일 모델
│       │   └── state_model.py        # 상태 관리 모델
│       │
│       ├── bases/          # 데이터베이스 모델 (SQLAlchemy)
│       │   ├── exam.py               # 시험 테이블 모델
│       │   ├── commentary.py         # 해설 테이블 모델
│       │   └── user.py               # 사용자 테이블 모델
│       │
│       ├── states/         # 상태 관리
│       │   ├── exam_state.py         # 시험 상태
│       │   ├── commentary_state.py   # 해설 상태
│       │   └── user_state.py        # 사용자 상태
│       │
│       └── repositories/   # 리포지토리 패턴
│           └── agent_repository.py  # 에이전트 리포지토리
│
├── tools/                  # 유틸리티 스크립트
│   ├── build_exam_dataset.py         # 시험 데이터셋 구축
│   ├── build_exam_dataset_from_md.py
│   ├── build_exam_dataset_marker.py
│   ├── ingest_exam_questions_to_neon.py
│   └── rebuild_md_from_pdf_marker.py
│
├── main.py                 # FastAPI 애플리케이션 진입점
├── config.py               # 설정 관리
├── dependencies.py         # FastAPI 의존성 주입
└── requirements.txt        # Python 패키지 의존성
```

## 🏗️ 아키텍처 패턴

### 1. 계층 구조 (Layered Architecture)

```
┌─────────────────────────────────────┐
│   API Layer (Routers)               │  ← HTTP 요청/응답 처리
│   /api/v1/admin/*                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Orchestrator Layer                │  ← 요청 분기 및 조율
│   (exam_flow, commentary_flow)     │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
┌──────▼──────┐  ┌─────▼──────┐
│  Service    │  │  Agent     │
│  (규칙 기반) │  │  (정책 기반) │
└─────────────┘  └─────────────┘
```

### 2. Orchestrator 패턴

**KoELECTRA 기반 분기 처리:**

```python
# exam_flow.py 예시
class ExamFlow:
    RULE_BASED_THRESHOLD_LOW = 0.3
    RULE_BASED_THRESHOLD_HIGH = 0.8

    async def process_exam_request():
        # 1. KoELECTRA로 요청 분석
        spam_prob = koelectra_result.get("spam_prob")

        # 2. 분기 처리
        if spam_prob < 0.3 or spam_prob > 0.8:
            # 규칙 기반 → exam_service
            return await exam_service.handle_request()
        else:
            # 정책 기반 → exam_agent (LLM 사용)
            return await exam_agent.handle_request()
```

### 3. Service vs Agent

| 구분 | Service (규칙 기반) | Agent (정책 기반) |
|------|-------------------|------------------|
| **용도** | 명확한 요청 처리 | 애매한 요청 처리 |
| **방법** | 정규식, DB 조회 | LLM 분석 |
| **속도** | 빠름 | 느림 |
| **예시** | "작년 회계학 3번" | "어떤 문제가 어려웠어?" |

## 🔄 요청 처리 흐름

### Exam 요청 처리 예시

```
1. 사용자 요청
   POST /api/v1/admin/exam/flow
   {"question": "작년 회계학 3번 정답 뭐야?"}

2. exam_router.py
   → ExamFlow.process_exam_request() 호출

3. exam_flow.py (Orchestrator)
   → KoELECTRA로 요청 분석
   → spam_prob < 0.3 → 규칙 기반 분기

4. exam_service.py (Service)
   → 정규식으로 파싱 (연도, 과목, 문항번호)
   → DB 조회
   → 결과 반환

5. exam_router.py
   → 응답 반환
```

### Chat 요청 처리 예시

```
1. 사용자 요청
   POST /api/v1/admin/chat
   {"question": "RAG란 무엇인가요?", "mode": "rag_openai"}

2. chat_router.py
   → mode에 따라 분기

3. retrieval/rag_agent.py
   → 벡터 검색 (pgvector)
   → OpenAI로 답변 생성
   → 결과 반환
```

## 📦 주요 컴포넌트

### 1. LLM 관리 (`core/llm/`)

- **BaseLLM**: 모든 LLM의 기본 추상 클래스
- **LLMFactory**: 팩토리 패턴으로 LLM 인스턴스 생성
- **ModelRegistry**: 모델 타입 등록 및 관리
- **Providers**:
  - `exaone_llm.py`: EXAONE 모델
  - `midm_llm.py`: Mi:dm 모델
  - `*_adapter.py`: 특정 작업용 어댑터

### 2. 데이터베이스 (`dependencies.py`)

- **connect_db()**: PostgreSQL 연결
- **get_db_connection()**: 전역 DB 연결 반환
- **setup_schema()**: 스키마 초기화 (pgvector 확장 등)

### 3. 모델 정의

**Pydantic 모델** (`domain/admin/models/`):
- API 요청/응답용
- 데이터 검증 및 직렬화

**SQLAlchemy 모델** (`domain/admin/bases/`):
- 데이터베이스 테이블 매핑
- ORM 사용

## 🔌 API 엔드포인트

### Base URL: `/api/v1/admin`

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/chat` | POST | 채팅/RAG API |
| `/exam/flow` | POST | 시험 정답 조회 (Orchestrator) |
| `/exam/answer` | POST | 시험 정답 조회 (직접) |
| `/exam/catalog` | GET | 시험 카탈로그 조회 |
| `/mcp/gateway` | POST | MCP 게이트웨이 |
| `/users/*` | - | 사용자 관리 |
| `/commentaries/*` | - | 해설 관리 |

## 🛠️ 설정 관리

### 환경 변수 (`.env`)

```bash
# 데이터베이스
DATABASE_URL=postgresql+psycopg://...
PGENGINE_URL=postgresql+asyncpg://...

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# 벡터 임베딩
EMBED_DIM=8

# 서버
HOST=0.0.0.0
PORT=8000

# CORS
CORS_ORIGINS=http://localhost:3000,https://example.com

# 모델 경로
MODEL_BASE_PATH=./artifacts
EXAONE_BASE_MODEL_PATH=./artifacts/base-models/exaone
MIDM_MODEL_PATH=./artifacts/base-models/midm
```

## 🚀 실행 방법

### 개발 서버 실행

```bash
# 프로젝트 루트에서
uvicorn backend.main:app --host localhost --port 8000 --reload
```

### 또는 Python으로 직접 실행

```bash
cd backend
python -m backend.main --server
```

## 📝 주요 패턴

### 1. 싱글톤 패턴
- Orchestrator 인스턴스 (exam_flow, commentary_flow 등)
- 전역 DB 연결

### 2. 팩토리 패턴
- LLMFactory: 모델 타입에 따라 LLM 인스턴스 생성

### 3. 레지스트리 패턴
- ModelRegistry: 모델 타입 등록 및 조회

### 4. 어댑터 패턴
- LLM Provider 어댑터들 (spam_filter, sentiment 등)

## 🔍 주요 의존성

- **FastAPI**: 웹 프레임워크
- **psycopg**: PostgreSQL 드라이버
- **pgvector**: 벡터 검색
- **SQLAlchemy**: ORM
- **Pydantic**: 데이터 검증
- **LangChain**: LLM 통합
- **transformers**: HuggingFace 모델

## 📚 참고 문서

- `ARCHITECTURE.md`: 상세 아키텍처 문서
- `domain/admin/services/README.md`: 서비스 레이어 설명

