# 데이터베이스 disconnected 문제 해결

## 🚨 문제

헬스 체크 응답:
```json
{"status":"ok","database":"disconnected"}
```

## 🔍 원인

헬스 체크 코드를 보면:
```python
conn = get_global_db_connection()  # 전역 DB 연결 가져오기
if conn and not conn.closed:
    db_status = "connected"
else:
    db_status = "disconnected"  # 연결이 없거나 닫혀있음
```

**가능한 원인:**
1. 서버 시작 시 DB 연결 실패
2. DB 연결이 끊어진 후 재연결 실패
3. `.env` 파일의 `DATABASE_URL` 설정 오류

## 🔧 해결 방법

### 1단계: EC2 서비스 로그 확인

**EC2 SSH 접속 후:**
```bash
# 최근 로그 확인 (DB 연결 관련)
sudo journalctl -u rag-api.service -n 100 --no-pager | grep -i "db\|database\|연결"

# 또는 전체 로그
sudo journalctl -u rag-api.service -n 100 --no-pager
```

**확인할 내용:**
- `[FastAPI] DB 연결 및 스키마 초기화 완료` 메시지가 있는지
- `[FastAPI] DB 초기화 실패` 또는 연결 오류 메시지가 있는지

### 2단계: EC2 .env 파일 확인

**EC2에서:**
```bash
cd /home/ubuntu/rag
cat .env | grep DATABASE_URL
```

**확인 사항:**
- `DATABASE_URL`이 설정되어 있는지
- URL 형식이 올바른지
- Neon DB URL이 유효한지

**예상 형식:**
```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
```

### 3단계: DB 연결 테스트

**EC2에서 직접 테스트:**
```bash
# Python으로 DB 연결 테스트
cd /home/ubuntu/rag
source venv/bin/activate
python3 -c "
from backend.config import settings
import psycopg
try:
    conn = psycopg.connect(settings.DATABASE_URL)
    print('✅ DB 연결 성공')
    conn.close()
except Exception as e:
    print(f'❌ DB 연결 실패: {e}')
"
```

### 4단계: 서비스 재시작

**EC2에서:**
```bash
# 서비스 재시작
sudo systemctl restart rag-api.service

# 로그 확인
sudo journalctl -u rag-api.service -f
```

**확인할 내용:**
- `[FastAPI] DB 연결 및 스키마 초기화 완료` 메시지
- 연결 오류 메시지

## 📝 체크리스트

### EC2 확인
- [ ] `.env` 파일에 `DATABASE_URL` 설정되어 있음
- [ ] `DATABASE_URL` 형식이 올바름
- [ ] 서비스 로그에 DB 연결 성공 메시지 있음
- [ ] Python으로 직접 DB 연결 테스트 성공

### 서비스 재시작
- [ ] 서비스 재시작 완료
- [ ] 재시작 후 헬스 체크: `{"status":"ok","database":"connected"}`

## ⚠️ 중요 사항

**`database: "disconnected"`는:**
- 서버 자체는 정상 작동 중 (`status: "ok"`)
- 하지만 DB 연결이 없거나 끊어진 상태

**해결 후:**
- 헬스 체크 응답: `{"status":"ok","database":"connected"}`
- RAG 기능도 정상 작동

## 🎯 즉시 조치

1. **EC2에서 서비스 로그 확인**
2. **`.env` 파일의 `DATABASE_URL` 확인**
3. **서비스 재시작**
4. **헬스 체크 재확인**

DB 연결이 정상이면 `database: "connected"`로 변경됩니다.
