# 프로젝트 구조 비교 분석

이 문서는 `ai.kroaddy.site` (마이크로서비스)와 현재 `backend` (모놀리식) 프로젝트의 구조 차이를 설명합니다.

## 📊 전체 비교 요약

| 항목 | ai.kroaddy.site | 현재 backend |
|------|-----------------|--------------|
| **아키텍처** | 마이크로서비스 | 모놀리식 |
| **서비스 수** | 5개 이상 (Gateway + Services) | 1개 (단일 애플리케이션) |
| **포트** | 여러 포트 (9000, 9002, 9003, 9004) | 단일 포트 (8000) |
| **데이터베이스** | ChromaDB (벡터), 파일 기반 | PostgreSQL + pgvector |
| **배포** | Docker Compose (여러 컨테이너) | 단일 컨테이너 또는 직접 실행 |
| **복잡도** | 높음 (서비스 간 통신) | 낮음 (모듈 간 호출) |

---

## 🏗️ 아키텍처 차이

### 1. ai.kroaddy.site (마이크로서비스)

```
ai.kroaddy.site/
├── gateway/              # API Gateway (포트 9000)
│   └── app/
│       ├── main.py       # 프록시 및 라우팅
│       └── agent/        # Agent 서비스
│
└── services/             # 독립적인 마이크로서비스들
    ├── authservice/      # 인증 서비스
    ├── chatbotservice/   # 챗봇 서비스 (포트 9004)
    │   └── rag.kroaddy.site/  # RAG 서브서비스 (포트 9002)
    ├── crawlerservice/   # 크롤링 서비스
    │   └── feed.kroaddy.site/  # Feed 서브서비스 (포트 9003)
    └── mlservice/        # ML 서비스
```

**특징:**
- ✅ 각 서비스가 독립적으로 배포 가능
- ✅ 서비스별로 다른 기술 스택 사용 가능
- ✅ 개별 서비스 확장 가능
- ❌ 서비스 간 통신 복잡도 증가
- ❌ 네트워크 지연 발생 가능
- ❌ 운영 복잡도 증가

### 2. 현재 backend (모놀리식)

```
backend/
├── main.py              # FastAPI 메인 애플리케이션
├── config.py            # 설정 관리
├── dependencies.py      # 의존성 주입
├── models.py            # Pydantic 모델
│
├── routers/             # API 라우터
│   ├── chat.py         # 채팅 엔드포인트
│   └── health.py        # 헬스 체크
│
├── services/            # 비즈니스 로직
│   ├── rag.py          # RAG 서비스
│   ├── chat_service.py # QLoRA 채팅 서비스
│   ├── database.py     # DB 작업
│   └── embedding.py    # 임베딩 생성
│
├── llm/                 # LLM 추상화 계층
│   ├── base.py         # BaseLLM 인터페이스
│   ├── factory.py      # LLM 팩토리
│   ├── loader.py       # 모델 로더
│   ├── registry.py     # 모델 레지스트리
│   └── implementations/
│       └── midm_llm.py # Mi:dm 구현
│
├── model/               # 로컬 모델 저장소
│   └── midm/           # Mi:dm 2.0 Mini 모델
│
└── data/                # 학습 데이터
    └── *.json          # 영화 리뷰 데이터
```

**특징:**
- ✅ 단순한 구조, 이해하기 쉬움
- ✅ 서비스 간 통신 오버헤드 없음
- ✅ 배포 및 운영이 간단
- ✅ 디버깅이 용이
- ❌ 서비스별 독립적 확장 어려움
- ❌ 기술 스택 변경이 전체에 영향

---

## 🔍 상세 비교

### 1. 서비스 분리 방식

#### ai.kroaddy.site
- **서비스별 독립 실행**: 각 서비스가 별도 프로세스/컨테이너
- **Gateway를 통한 통합**: 모든 요청이 Gateway를 거침
- **서비스 간 HTTP 통신**: REST API로 통신

```python
# Gateway에서 다른 서비스 호출
FEED_SERVICE_URL = "http://feedservice:9003"
RAG_SERVICE_URL = "http://ragservice:9002"
CHATBOT_SERVICE_URL = "http://chatbotservice:9004"
```

#### 현재 backend
- **모듈 기반 분리**: Python 모듈로 기능 분리
- **직접 함수 호출**: 모듈 간 직접 import 및 호출
- **의존성 주입**: FastAPI Depends 사용

```python
# routers/chat.py에서 services 직접 호출
from backend.services.rag import rag_with_llm, openai_only
from backend.services.database import search_similar
```

### 2. 데이터베이스 구조

#### ai.kroaddy.site
- **ChromaDB**: 벡터 데이터베이스 (RAG 서비스)
- **파일 기반**: CSV, JSON 파일 저장
- **서비스별 독립 DB**: 각 서비스가 자체 저장소 사용

```
chatbotservice/rag.kroaddy.site/
└── vector_db/
    └── chroma_db/      # ChromaDB 저장소
```

#### 현재 backend
- **PostgreSQL + pgvector**: 관계형 DB + 벡터 확장
- **통합 데이터베이스**: 모든 기능이 하나의 DB 사용
- **LangChain 통합**: `langchain-postgres` 사용



### 3. LLM 통합 방식

#### ai.kroaddy.site
- **외부 LLM API**: OpenAI API 사용
- **Agent 서비스**: Gateway에서 LLM API 통합
- **SLLM 관리**: 별도 데이터베이스로 관리

```python
# gateway/app/agent/llm_api.py
# LLM API 클라이언트로 외부 서비스 호출
```

#### 현재 backend
- **다중 LLM 지원**: OpenAI + 로컬 LLM (Mi:dm)
- **추상화 계층**: BaseLLM 인터페이스로 통일
- **로컬 모델 실행**: QLoRA로 로컬 모델 학습 및 실행

```python
# backend/llm/base.py
class BaseLLM:
    def load(self) -> None: ...
    def generate(self, prompt: str) -> str: ...

# backend/llm/implementations/midm_llm.py
class Mi:dmLLM(BaseLLM): ...
```

### 4. RAG 구현 방식

#### ai.kroaddy.site
- **별도 RAG 서비스**: `rag.kroaddy.site` 독립 서비스
- **ChromaDB 사용**: 벡터 스토어로 ChromaDB
- **서비스 간 통신**: HTTP로 RAG 서비스 호출

```
chatbotservice/rag.kroaddy.site/
├── app/
│   ├── embeddings.py    # 임베딩 생성
│   ├── rag_engine.py   # RAG 엔진
│   └── vector_store.py # 벡터 스토어
└── vector_db/chroma_db/
```

#### 현재 backend
- **통합 RAG 모듈**: `services/rag.py`에 구현
- **pgvector 사용**: PostgreSQL 확장으로 벡터 검색
- **함수 호출**: 직접 함수 호출로 RAG 실행

```python
# backend/services/rag.py
def rag_with_llm(question: str, retrieved_docs: Sequence[str]) -> str:
    llm = ChatOpenAI(...)
    prompt = _build_rag_prompt(question, retrieved_docs)
    return llm.invoke(prompt).content
```

### 5. 크롤링 기능

#### ai.kroaddy.site
- **전용 크롤링 서비스**: `crawlerservice` 독립 서비스
- **다양한 크롤러**: 카카오맵, 네이버, 다음, 구글 등
- **Feed 서비스**: 별도 서브서비스로 분리

```
crawlerservice/
├── app/
│   ├── bs_demo/        # BeautifulSoup 크롤러
│   │   ├── overcharge_detection/  # 바가지 탐지
│   │   └── risk_detection/        # 위험 탐지
│   └── sel_demo/       # Selenium 크롤러
└── feed.kroaddy.site/  # Feed 서비스
```

#### 현재 backend
- **크롤링 기능 없음**: RAG 및 챗봇에 집중
- **데이터는 정적**: `backend/data/`의 JSON 파일 사용

### 6. ML/AI 기능

#### ai.kroaddy.site
- **전용 ML 서비스**: `mlservice` 독립 서비스
- **다양한 분석**: NLP, 범죄 데이터, 타이타닉 등
- **모델 저장**: KoELECTRA 등 로컬 모델

```
mlservice/
├── app/
│   ├── nlp/            # 자연어 처리
│   ├── seoul_crime/    # 범죄 데이터 분석
│   ├── titanic/        # 타이타닉 분석
│   └── resources/      # 모델 및 데이터
│       └── koelectra_local/
```

#### 현재 backend
- **QLoRA 학습**: `chat_service.py`에 구현
- **로컬 모델 실행**: Mi:dm 2.0 Mini 사용
- **학습 데이터**: `backend/data/`의 영화 리뷰

```python
# backend/services/chat_service.py
class QLoRAChatService:
    def generate(self, prompt: str, ...) -> str: ...
    # QLoRA 어댑터로 모델 사용
```

---

## 📦 의존성 및 기술 스택

### ai.kroaddy.site

```python
# 각 서비스별 requirements.txt
- FastAPI
- Uvicorn
- Selenium (크롤링)
- BeautifulSoup (파싱)
- ChromaDB (벡터 DB)
- KoELECTRA (한국어 모델)
- Pandas, Matplotlib (데이터 분석)
```

### 현재 backend

```python
# backend/requirements.txt
- FastAPI
- Uvicorn
- langchain (RAG 프레임워크)
- langchain-openai (OpenAI 통합)
- langchain-postgres (PostgreSQL 통합)
- pgvector (벡터 확장)
- transformers (로컬 LLM)
- torch (딥러닝)
- peft (QLoRA)
```

---

## 🚀 배포 방식

### ai.kroaddy.site

```yaml
# docker-compose.yml
services:
  gateway:
    ports: ["9000:9000"]
  rag-service:
    ports: ["9002:9002"]
  feed-service:
    ports: ["9003:9003"]
  chatbot-service:
    ports: ["9004:9004"]
```

**특징:**
- 여러 컨테이너 동시 실행
- 서비스별 독립 스케일링
- 네트워크 설정 필요

### 현재 backend

```bash
# 단일 서버 실행
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 또는 Docker
docker run -p 8000:8000 backend
```

**특징:**
- 단일 프로세스/컨테이너
- 간단한 배포
- 수직 확장만 가능

---

## 🎯 사용 사례별 적합성

### ai.kroaddy.site가 적합한 경우

- ✅ 여러 팀이 독립적으로 개발
- ✅ 서비스별로 다른 기술 스택 필요
- ✅ 서비스별 독립적 확장 필요
- ✅ 복잡한 비즈니스 로직 분리
- ✅ 다양한 기능 (크롤링, ML, RAG 등)

### 현재 backend가 적합한 경우

- ✅ 소규모 팀 또는 개인 프로젝트
- ✅ 빠른 개발 및 배포 필요
- ✅ 단순한 아키텍처 선호
- ✅ RAG 및 챗봇에 집중
- ✅ 운영 복잡도 최소화

---

## 🔄 마이그레이션 고려사항

### 현재 backend → 마이크로서비스로 전환 시

1. **서비스 분리**
   - RAG 서비스 분리
   - QLoRA 서비스 분리
   - LLM 서비스 분리

2. **통신 방식 변경**
   - 함수 호출 → HTTP API
   - 공유 DB → 서비스별 DB 또는 API 통신

3. **Gateway 추가**
   - API Gateway 구현
   - 라우팅 및 인증 처리

4. **배포 파이프라인**
   - 각 서비스별 CI/CD
   - Docker Compose 또는 Kubernetes

### ai.kroaddy.site → 모놀리식으로 전환 시

1. **서비스 통합**
   - 모든 서비스를 하나의 애플리케이션으로 통합
   - 모듈 기반 구조로 재구성

2. **데이터베이스 통합**
   - ChromaDB → pgvector로 마이그레이션
   - 파일 기반 → DB 기반

3. **의존성 통합**
   - 각 서비스의 requirements.txt 통합
   - 충돌 해결

---

## 📝 결론

| 측면 | ai.kroaddy.site | 현재 backend |
|------|-----------------|--------------|
| **복잡도** | 높음 | 낮음 |
| **확장성** | 높음 (수평 확장) | 중간 (수직 확장) |
| **개발 속도** | 느림 (서비스 간 통신) | 빠름 (직접 호출) |
| **운영 복잡도** | 높음 | 낮음 |
| **유지보수** | 어려움 (여러 서비스) | 쉬움 (단일 코드베이스) |
| **적용 범위** | 대규모 프로젝트 | 소규모~중규모 프로젝트 |

**권장사항:**
- **현재 backend**: RAG 및 챗봇에 집중하는 프로젝트에 적합
- **ai.kroaddy.site**: 다양한 기능과 독립적 확장이 필요한 프로젝트에 적합
