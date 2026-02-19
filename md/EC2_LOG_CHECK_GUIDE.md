# EC2 로그 확인 가이드

## 🔍 로그 확인 명령어

### 1. 서비스 로그 확인 (가장 중요)

**EC2 SSH 접속 후:**

```bash
# 최근 100줄 로그 확인
sudo journalctl -u rag-api.service -n 100 --no-pager

# 실시간 로그 확인 (Ctrl+C로 종료)
sudo journalctl -u rag-api.service -f

# 특정 시간대 로그 확인
sudo journalctl -u rag-api.service --since "1 hour ago"

# 오류만 필터링
sudo journalctl -u rag-api.service -n 200 --no-pager | grep -i "error\|fail\|exception"
```

### 2. 전체 시스템 로그 확인

```bash
# 시스템 로그 확인
sudo journalctl -n 100 --no-pager

# 네트워크 관련 로그
sudo journalctl -n 100 --no-pager | grep -i "network\|connection\|port"
```

### 3. uvicorn 프로세스 로그 확인

```bash
# 프로세스 확인
ps aux | grep uvicorn

# 프로세스 ID로 로그 확인
sudo journalctl _PID=1681 -n 100 --no-pager
```

### 4. 네트워크 연결 로그 확인

```bash
# 포트 리스닝 확인
sudo ss -tuln | grep 8000

# 활성 연결 확인
sudo ss -tn | grep 8000

# 네트워크 통계
sudo netstat -s | grep -i "connection\|timeout"
```

## 📊 로그에서 확인할 내용

### 정상적인 로그

```
INFO:     Started server process [1681]
INFO:     Waiting for application startup.
[FastAPI] 서버 시작 중...
[FastAPI] DB 연결 및 스키마 초기화 완료
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 외부 요청이 들어오는 경우

```
INFO:     123.456.789.0:54321 - "GET /health HTTP/1.1" 200 OK
INFO:     123.456.789.0:54322 - "GET /docs HTTP/1.1" 200 OK
```

### 문제가 있는 경우

```
ERROR:    [오류 메시지]
[FastAPI] DB 초기화 실패: [오류]
```

## 🔧 문제 진단 단계

### Step 1: 서비스 로그 확인

```bash
# 최근 로그 확인
sudo journalctl -u rag-api.service -n 200 --no-pager
```

**확인할 내용:**
- 서비스가 정상적으로 시작되었는지
- 데이터베이스 연결이 성공했는지
- 외부 요청이 들어오는지 (IP 주소 확인)

### Step 2: 실시간 로그 모니터링

```bash
# 실시간 로그 확인
sudo journalctl -u rag-api.service -f
```

**그 다음:**
- 브라우저에서 `http://13.125.210.86:8000/health` 접속 시도
- 로그에 요청이 나타나는지 확인

### Step 3: 네트워크 연결 확인

```bash
# 포트 리스닝 확인
sudo ss -tuln | grep 8000

# 활성 연결 확인
sudo ss -tn | grep 8000

# 방화벽 상태 확인
sudo ufw status
```

## 🚨 일반적인 문제와 해결

### 문제 1: 로그에 외부 요청이 없음

**의미:** 외부에서 요청이 EC2에 도달하지 않음

**가능한 원인:**
- AWS 보안 그룹 설정 문제
- 네트워크 ACL 문제
- 라우팅 문제

**해결:**
- AWS 보안 그룹 인바운드 규칙 재확인
- VPC 네트워크 ACL 확인

### 문제 2: 로그에 오류 메시지

**의미:** 서비스 내부 오류

**해결:**
- 오류 메시지 확인
- 데이터베이스 연결 확인
- 환경 변수 확인

### 문제 3: 로그에 요청은 있지만 응답이 없음

**의미:** 서비스가 요청을 받지만 처리하지 못함

**해결:**
- 애플리케이션 로그 확인
- 데이터베이스 연결 확인
- 메모리/CPU 사용량 확인

## 📝 로그 저장 및 분석

### 로그를 파일로 저장

```bash
# 로그를 파일로 저장
sudo journalctl -u rag-api.service -n 500 --no-pager > /tmp/rag-api.log

# 파일 확인
cat /tmp/rag-api.log
```

### 로그 분석

```bash
# 오류만 추출
sudo journalctl -u rag-api.service -n 500 --no-pager | grep -i "error" > /tmp/errors.log

# 요청 통계
sudo journalctl -u rag-api.service -n 500 --no-pager | grep "GET\|POST" | wc -l

# IP 주소별 요청 확인
sudo journalctl -u rag-api.service -n 500 --no-pager | grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" | sort | uniq -c
```
