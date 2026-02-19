# EC2 외부 접근 불가 해결 가이드

## 🔍 문제 확인

**증상:**
- ✅ EC2 서비스는 실행 중 (`active (running)`)
- ❌ 브라우저에서 `13.125.210.86:8000/docs` 접속 불가
- ❌ `ERR_CONNECTION_TIMED_OUT` 오류

## 🚨 가능한 원인

### 1. EC2 보안 그룹 설정 (가장 가능성 높음)

포트 8000이 외부에서 접근 가능하도록 설정되어 있는지 확인 필요.

### 2. EC2 내부 방화벽 (UFW)

Ubuntu 방화벽에서 포트 8000이 차단되어 있을 수 있음.

### 3. 서비스가 실제로 리스닝하지 않음

서비스가 실행 중이지만 포트 8000에서 리스닝하지 않을 수 있음.

## 🔧 해결 방법

### 해결 1: EC2에서 포트 리스닝 확인

**EC2 SSH 접속 후:**

```bash
# 포트 8000이 리스닝 중인지 확인
sudo netstat -tuln | grep 8000
# 또는
sudo ss -tuln | grep 8000
```

**예상 결과:**
```
tcp  0  0  0.0.0.0:8000  0.0.0.0:*  LISTEN
```

포트가 리스닝 중이 아니면 서비스가 제대로 시작되지 않은 것입니다.

### 해결 2: EC2 내부 방화벽 확인

**EC2에서:**

```bash
# UFW 방화벽 상태 확인
sudo ufw status

# 포트 8000이 열려있지 않으면
sudo ufw allow 8000/tcp
sudo ufw reload
```

### 해결 3: EC2 보안 그룹 재확인

**AWS 콘솔에서:**

1. **EC2 콘솔** → **인스턴스** → 인스턴스 선택
2. **보안** 탭 → **보안 그룹** 클릭
3. **인바운드 규칙** 확인:
   - 포트 `8000`이 있는지 확인
   - 소스가 `0.0.0.0/0`인지 확인

**규칙이 없으면 추가:**
- 유형: `사용자 지정 TCP`
- 포트: `8000`
- 소스: `0.0.0.0/0`
- 설명: `FastAPI API`

### 해결 4: 서비스 로그 확인

**EC2에서:**

```bash
# 최근 로그 확인
sudo journalctl -u rag-api.service -n 100 --no-pager

# 실시간 로그 확인
sudo journalctl -u rag-api.service -f
```

**확인할 내용:**
- 서비스가 정상적으로 시작되었는지
- 포트 8000에서 리스닝 중인지
- 오류 메시지가 있는지

### 해결 5: EC2 내부에서 테스트

**EC2에서:**

```bash
# 로컬에서 헬스 체크
curl http://localhost:8000/health

# 외부 IP로 테스트 (EC2 내부에서)
curl http://13.125.210.86:8000/health
```

## ✅ 확인 체크리스트

- [ ] EC2에서 포트 8000 리스닝 확인 (`netstat` 또는 `ss`)
- [ ] EC2 UFW 방화벽에서 포트 8000 허용 확인
- [ ] AWS 보안 그룹에서 포트 8000 인바운드 규칙 확인
- [ ] EC2 내부에서 `curl localhost:8000/health` 성공 확인
- [ ] 서비스 로그에서 오류 확인

## 🧪 단계별 진단

### Step 1: 포트 리스닝 확인

```bash
# EC2에서
sudo ss -tuln | grep 8000
```

**성공 시:**
```
tcp   LISTEN  0  128  0.0.0.0:8000  0.0.0.0:*
```

**실패 시:** 서비스가 제대로 시작되지 않음

### Step 2: 방화벽 확인

```bash
# EC2에서
sudo ufw status
sudo ufw allow 8000/tcp
sudo ufw reload
```

### Step 3: 보안 그룹 확인

AWS 콘솔에서 인바운드 규칙 확인

### Step 4: 로컬 테스트

```bash
# EC2에서
curl http://localhost:8000/health
```

**예상 응답:**
```json
{"status":"healthy","database":"connected"}
```

## 🆘 여전히 문제가 있으면

1. **EC2 인스턴스 재시작**
   ```bash
   # AWS 콘솔에서 인스턴스 재시작
   ```

2. **서비스 재시작**
   ```bash
   sudo systemctl restart rag-api.service
   ```

3. **포트 변경 테스트**
   - 임시로 다른 포트(예: 8001)로 변경하여 테스트
