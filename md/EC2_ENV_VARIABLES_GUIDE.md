# EC2 .env 파일 환경 변수 가이드

## ✅ 필수 환경 변수 (이미 설정 완료)

다음 변수들은 이미 올바르게 설정되어 있습니다:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
OPENAI_API_KEY=your_openai_key_here
CORS_ORIGINS=https://rag-nine-cyan.vercel.app,https://rag-nine-cyan-*.vercel.app,http://localhost:3000
```

## ❌ 설정 불필요한 변수들

### 1. PGENGINE_URL
- **설정 불필요**: `DATABASE_URL`에서 자동으로 생성됩니다
- **코드 위치**: `backend/config.py` 59번 줄
- **자동 변환**: `postgresql+psycopg://` → `postgresql+asyncpg://`
- **기본값**: `DATABASE_URL`을 기반으로 자동 생성

### 2. CONNECTION_STRING
- **사용되지 않음**: 코드에서 이 변수를 사용하지 않습니다
- **대신 사용**: `DATABASE_URL`이 사용됩니다

### 3. LLM_PROVIDER
- **사용되지 않음**: 코드에서 이 변수를 사용하지 않습니다
- **대신 사용**: `DEFAULT_MODEL_TYPE` 환경 변수 (기본값: "midm")

### 4. LOCAL_MODEL_DIR
- **사용되지 않음**: 코드에서 이 변수를 사용하지 않습니다
- **대신 사용**: `MODEL_BASE_PATH` 환경 변수 (기본값: "./model")

## 📝 선택적 환경 변수 (기본값 사용 가능)

다음 변수들은 선택적으로 설정할 수 있지만, 기본값이 있어서 설정하지 않아도 됩니다:

```env
# OpenAI 모델 설정 (기본값: "gpt-4o-mini")
OPENAI_MODEL=gpt-4o-mini

# 벡터 임베딩 차원 (기본값: 8)
EMBED_DIM=8

# 서버 설정 (기본값: 0.0.0.0:8000)
HOST=0.0.0.0
PORT=8000

# LLM 모델 경로 (기본값: "./model")
MODEL_BASE_PATH=./model

# 기본 모델 타입 (기본값: "midm")
DEFAULT_MODEL_TYPE=midm

# 기본 모델 이름 (기본값: "midm")
DEFAULT_MODEL_NAME=midm
```

## 🔧 QLoRA 관련 선택적 환경 변수

QLoRA 기능을 사용하는 경우에만 필요합니다:

```env
# LoRA 어댑터 경로 (선택사항)
LORA_ADAPTER_PATH=/path/to/lora/adapter

# 양자화 설정 (선택사항, 기본값: 4-bit=true, 8-bit=false)
LOAD_IN_4BIT=true
LOAD_IN_8BIT=false
```

## ✅ 최종 .env 파일 예시

**최소 설정 (현재 설정):**
```env
# 필수
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
OPENAI_API_KEY=your_openai_key_here
CORS_ORIGINS=https://rag-nine-cyan.vercel.app,https://rag-nine-cyan-*.vercel.app,http://localhost:3000
```

**완전한 설정 (모든 옵션 포함):**
```env
# 필수
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
OPENAI_API_KEY=your_openai_key_here
CORS_ORIGINS=https://rag-nine-cyan.vercel.app,https://rag-nine-cyan-*.vercel.app,http://localhost:3000

# 선택적 (기본값 사용 가능)
OPENAI_MODEL=gpt-4o-mini
EMBED_DIM=8
HOST=0.0.0.0
PORT=8000
MODEL_BASE_PATH=./model
DEFAULT_MODEL_TYPE=midm
DEFAULT_MODEL_NAME=midm

# QLoRA (선택사항)
# LORA_ADAPTER_PATH=/path/to/adapter
# LOAD_IN_4BIT=true
# LOAD_IN_8BIT=false
```

## 🎯 결론

**현재 설정으로 충분합니다!**

- ✅ `DATABASE_URL`: 설정 완료
- ✅ `OPENAI_API_KEY`: 설정 완료
- ✅ `CORS_ORIGINS`: 설정 완료
- ❌ `PGENGINE_URL`: **설정 불필요** (자동 생성)
- ❌ `CONNECTION_STRING`: **설정 불필요** (사용되지 않음)
- ❌ `LLM_PROVIDER`: **설정 불필요** (사용되지 않음)
- ❌ `LOCAL_MODEL_DIR`: **설정 불필요** (사용되지 않음)

추가 설정 없이 현재 상태로 서비스를 재시작하면 됩니다!
