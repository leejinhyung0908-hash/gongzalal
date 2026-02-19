# Neon DB 설정 가이드

## EC2에서 Neon DB 설정하기

### 1. EC2에 SSH 접속

```bash
ssh -i "kroaddy.pem" ubuntu@ec2-13-125-210-86.ap-northeast-2.compute.amazonaws.com
```

### 2. .env 파일 수정

```bash
# .env 파일 편집
nano /home/ubuntu/rag/.env
```

다음 내용으로 수정:

```env
# Neon DB URL (Neon 콘솔에서 복사한 URL)
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require

# 또는 asyncpg 형식 (PGENGINE_URL이 필요한 경우)
PGENGINE_URL=postgresql+asyncpg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require

# OpenAI 설정 (선택사항)
# OPENAI_API_KEY=your_key_here
```

### 3. Neon DB URL 형식

Neon DB에서 제공하는 연결 문자열은 다음과 같은 형식입니다:

```
postgresql://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
```

이를 `postgresql+psycopg://` 형식으로 변환:

```
postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
```

### 4. 파일 저장 및 서비스 재시작

```bash
# 파일 저장 (nano에서 Ctrl+O, Enter, Ctrl+X)

# 서비스 재시작
sudo systemctl restart rag-api.service

# 서비스 상태 확인
sudo systemctl status rag-api.service

# 헬스 체크
curl http://localhost:8000/health
```

### 5. Neon DB에서 pgvector 확장 확인

Neon DB는 pgvector를 지원합니다. 연결 후 자동으로 확장이 생성됩니다.

## 로컬 개발 환경 설정

로컬 `.env` 파일에도 동일한 Neon DB URL을 설정하세요:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
```
