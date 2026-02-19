# OpenAI 설정 가이드

이 문서는 backend에서 OpenAI를 사용하기 위해 필요한 파일과 설정 방법을 설명합니다.

## 📋 필요한 파일 목록

### 1. 필수 파일

#### `backend/config.py`
- **역할**: OpenAI 설정을 관리하는 설정 클래스
- **주요 설정**:
  ```python
  OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
  OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
  ```
- **설명**: 환경 변수에서 OpenAI API 키와 모델명을 읽어옵니다.

#### `backend/services/rag.py`
- **역할**: OpenAI를 사용하는 RAG 함수들
- **주요 함수**:
  - `rag_with_llm()`: RAG + OpenAI 조합
  - `openai_only()`: OpenAI만 사용 (RAG 없이)
- **의존성**: `langchain_openai.ChatOpenAI` 사용

#### `backend/routers/chat.py`
- **역할**: OpenAI 모드를 처리하는 API 엔드포인트
- **주요 기능**:
  - `mode="openai"`: OpenAI만 사용
  - `mode="rag_openai"`: RAG + OpenAI (기본값)
- **검증**: `settings.OPENAI_API_KEY`가 없으면 에러 반환

#### `.env` 파일 (프로젝트 루트)
- **역할**: 환경 변수 저장
- **필수 변수**:
  ```env
  OPENAI_API_KEY=sk-...
  OPENAI_MODEL=gpt-4o-mini
  ```
- **주의**: `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다.

#### `backend/requirements.txt`
- **역할**: Python 패키지 의존성
- **필수 패키지**:
  ```
  langchain-openai>=0.2.0
  ```
- **설치**: `pip install -r backend/requirements.txt`

### 2. 선택적 파일

#### `backend/main.py`
- **역할**: CLI 모드에서 OpenAI 키 확인
- **기능**: OpenAI 키가 있으면 LLM 기반 RAG 사용, 없으면 규칙 기반 RAG 사용

## 🔧 설정 방법

### 1단계: `.env` 파일 생성

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가:

```env
# OpenAI 설정
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini

# 기타 설정 (선택사항)
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
PGENGINE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

### 2단계: 의존성 설치

```bash
pip install -r backend/requirements.txt
```

또는 특정 패키지만 설치:

```bash
pip install langchain-openai>=0.2.0
```

### 3단계: 환경 변수 확인

애플리케이션 시작 시 다음 로그가 출력되면 정상:

```
[정보] OPENAI_API_KEY가 설정되어 있어 LLM 기반 RAG를 사용합니다.
```

## 📝 사용 방법

### API 엔드포인트

#### 1. OpenAI만 사용 (`mode="openai"`)

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "LangChain이 무엇인가요?",
    "mode": "openai"
  }'
```

#### 2. RAG + OpenAI (`mode="rag_openai"`)

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "LangChain과 pgvector로 RAG 시스템을 어떻게 만들 수 있어?",
    "mode": "rag_openai",
    "top_k": 3
  }'
```

### 코드에서 직접 사용

```python
from backend.config import settings
from backend.services.rag import rag_with_llm, openai_only

# OpenAI만 사용
if settings.OPENAI_API_KEY:
    answer = openai_only("질문 내용")

# RAG + OpenAI
if settings.OPENAI_API_KEY:
    retrieved_docs = ["문서1", "문서2"]
    answer = rag_with_llm("질문 내용", retrieved_docs)
```

## 🔍 설정 확인 방법

### 1. 환경 변수 확인

```python
from backend.config import settings

print(f"API Key 설정됨: {settings.OPENAI_API_KEY is not None}")
print(f"모델: {settings.OPENAI_MODEL}")
```

### 2. API 테스트

```bash
# 헬스 체크
curl http://localhost:8000/health

# OpenAI 모드 테스트
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "테스트", "mode": "openai"}'
```

## ⚠️ 주의사항

### 1. API 키 보안

- `.env` 파일은 **절대 Git에 커밋하지 마세요**
- `.gitignore`에 이미 포함되어 있습니다
- 프로덕션 환경에서는 환경 변수로 직접 설정하거나 시크릿 관리 서비스 사용

### 2. API 키 형식

- OpenAI API 키는 `sk-`로 시작합니다
- 예: `sk-proj-...` (새 형식) 또는 `sk-...` (구 형식)

### 3. 모델 선택

- 기본값: `gpt-4o-mini` (비용 효율적)
- 다른 모델 사용 시 `.env`에서 변경:
  ```env
  OPENAI_MODEL=gpt-4o
  OPENAI_MODEL=gpt-3.5-turbo
  ```

### 4. API 키 없이 동작

- OpenAI 키가 없어도 애플리케이션은 정상 동작합니다
- `mode="rag"` 또는 `mode="local"` 사용 가능
- `mode="rag_openai"`는 자동으로 `mode="rag"`로 폴백

## 🐛 문제 해결

### 문제 1: "OPENAI_API_KEY가 설정되지 않았습니다"

**원인**: `.env` 파일이 없거나 환경 변수가 로드되지 않음

**해결**:
1. 프로젝트 루트에 `.env` 파일 생성 확인
2. `backend/config.py`에서 `load_dotenv()` 호출 확인
3. 환경 변수 직접 설정:
   ```bash
   export OPENAI_API_KEY=sk-...
   ```

### 문제 2: "ModuleNotFoundError: No module named 'langchain_openai'"

**원인**: 패키지가 설치되지 않음

**해결**:
```bash
pip install langchain-openai>=0.2.0
```

### 문제 3: API 호출 실패

**원인**: 잘못된 API 키 또는 네트워크 문제

**해결**:
1. API 키 유효성 확인
2. OpenAI 계정 상태 확인
3. 네트워크 연결 확인
4. API 사용량 한도 확인

## 📚 관련 파일 구조

```
backend/
├── config.py              # 설정 관리 (OpenAI 키, 모델)
├── services/
│   └── rag.py            # OpenAI 사용 함수들
├── routers/
│   └── chat.py           # API 엔드포인트
└── requirements.txt      # langchain-openai 의존성

.env                      # 환경 변수 (Git에 커밋 안 됨)
```

## 🔗 참고 자료

- [LangChain OpenAI 문서](https://python.langchain.com/docs/integrations/chat/openai)
- [OpenAI API 문서](https://platform.openai.com/docs/api-reference)
- [python-dotenv 문서](https://pypi.org/project/python-dotenv/)
