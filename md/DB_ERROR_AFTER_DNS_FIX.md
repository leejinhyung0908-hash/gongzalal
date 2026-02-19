# DNS 캐시 클리어 후 DB error 문제

## 🚨 문제

로컬에서 도메인 연결 테스트:
```json
{"status":"ok","database":"error"}
```

**의미:**
- 서버는 정상 작동 중 (`status: "ok"`)
- DB 연결은 있지만 쿼리 실행 중 예외 발생 (`database: "error"`)

## 🔍 원인 분석

헬스 체크 코드:
```python
try:
    if conn is None:
        db_status = "disconnected"
    elif conn.closed:
        db_status = "disconnected"
    else:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")  # 여기서 예외 발생 가능
        db_status = "connected"
except Exception as e:
    print(f"[Health] DB 체크 오류: {e}", flush=True)
    db_status = "error"  # 예외 발생 시 "error"
```

**가능한 원인:**
1. DB 연결이 끊어졌지만 `conn.closed`가 제대로 감지되지 않음
2. 쿼리 실행 중 네트워크 문제
3. Neon DB 서버 문제
4. 연결 타임아웃

## 🔧 해결 방법

### 1단계: EC2에서 서비스 로그 확인

**EC2 SSH 접속 후:**
```bash
# 최근 로그 확인 (DB 오류 관련)
sudo journalctl -u rag-api.service -n 100 --no-pager | grep -i "health\|db\|error"

# 또는 전체 로그
sudo journalctl -u rag-api.service -n 100 --no-pager
```

**확인할 내용:**
- `[Health] DB 체크 오류: ...` 메시지
- DB 연결 관련 오류 메시지

### 2단계: EC2에서 직접 헬스 체크

**EC2에서:**
```bash
# EC2에서 로컬 서버로 테스트
curl http://localhost:8000/health
```

**결과 비교:**
- EC2에서 `connected` → 로컬에서 `error` → 네트워크 문제 가능
- EC2에서도 `error` → DB 연결 문제

### 3단계: 서비스 재시작

**EC2에서:**
```bash
# 서비스 재시작
sudo systemctl restart rag-api.service

# 로그 확인
sudo journalctl -u rag-api.service -f
```

### 4단계: Neon DB 연결 확인

**EC2에서 직접 DB 연결 테스트:**
```bash
cd /home/ubuntu/rag
source venv/bin/activate
python3 -c "
from backend.config import settings
import psycopg
try:
    conn = psycopg.connect(settings.DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute('SELECT 1')
    print('✅ DB 연결 및 쿼리 성공')
    conn.close()
except Exception as e:
    print(f'❌ DB 연결/쿼리 실패: {e}')
"
```

## 📝 체크리스트

### EC2 확인
- [ ] EC2에서 `curl http://localhost:8000/health` 결과 확인
- [ ] 서비스 로그에서 `[Health] DB 체크 오류` 메시지 확인
- [ ] Python으로 직접 DB 연결 테스트

### 서비스 재시작
- [ ] 서비스 재시작 완료
- [ ] 재시작 후 헬스 체크: `{"status":"ok","database":"connected"}`

## ⚠️ 중요 사항

**`database: "error"`는:**
- 서버는 정상 작동 중
- DB 연결은 있지만 쿼리 실행 중 예외 발생
- 일시적인 네트워크 문제일 수 있음

**해결 후:**
- 헬스 체크 응답: `{"status":"ok","database":"connected"}`
- RAG 기능도 정상 작동

## 🎯 즉시 조치

1. **EC2에서 서비스 로그 확인** (오류 메시지 확인)
2. **EC2에서 헬스 체크** (`localhost`로 테스트)
3. **서비스 재시작**
4. **다시 테스트**

EC2에서 위 명령어를 실행하고 결과를 알려주세요. 특히 서비스 로그에서 `[Health] DB 체크 오류` 메시지를 확인해 주세요.

