# Vercel → EC2 연결 타임아웃 해결 가이드

## 🔍 오류 분석

**오류 메시지:**
```
ConnectTimeoutError: Connect Timeout Error
(attempted address: 13.125.210.86:8000, timeout: 10000ms)
```

**의미:**
- ✅ `BACKEND_URL` 환경 변수는 올바르게 설정되어 있습니다 (`13.125.210.86:8000`)
- ❌ Vercel 서버리스 함수에서 EC2로 연결할 수 없습니다
- ❌ 10초 타임아웃 내에 연결이 실패했습니다

## 🚨 즉시 확인할 사항

### 1. EC2 보안 그룹 확인 (가장 중요!)

**AWS 콘솔에서:**

1. **EC2 콘솔** → **인스턴스** → 인스턴스 선택
2. **보안** 탭 → **보안 그룹** 클릭
3. **인바운드 규칙** 확인:
   - 포트 `8000`이 열려있는지 확인
   - 소스가 `0.0.0.0/0` (모든 IP)인지 확인

**규칙이 없거나 제한적이면:**

1. **인바운드 규칙 편집** 클릭
2. **규칙 추가** 클릭
3. 다음 설정:
   - **유형**: `사용자 지정 TCP`
   - **포트**: `8000`
   - **소스**: `0.0.0.0/0` (모든 IPv4 주소)
   - **설명**: `Vercel API access`
4. **규칙 저장** 클릭

### 2. EC2 서비스 상태 확인

**EC2 SSH 접속 후:**

```bash
# 서비스 상태 확인
sudo systemctl status rag-api.service

# 실행 중이 아니면 시작
sudo systemctl start rag-api.service
sudo systemctl enable rag-api.service

# 헬스 체크
curl http://localhost:8000/health
```

**예상 응답:**
```json
{"status":"healthy","database":"connected"}
```

### 3. EC2 외부 접근 테스트

**로컬 컴퓨터에서 (Windows PowerShell):**

```powershell
# EC2 IP로 직접 테스트
curl http://13.125.210.86:8000/health

# 또는
Invoke-WebRequest -Uri "http://13.125.210.86:8000/health" -Method GET
```

**성공하면:**
```json
{"status":"healthy","database":"connected"}
```

**실패하면:**
- 보안 그룹 설정 문제
- EC2 서비스가 실행되지 않음
- 네트워크 ACL 문제

### 4. EC2 인스턴스 상태 확인

**AWS 콘솔에서:**

1. **EC2 콘솔** → **인스턴스**
2. 인스턴스 상태 확인:
   - ✅ `running` (실행 중)이어야 합니다
   - ❌ `stopped` (중지됨)이면 시작해야 합니다
   - ❌ `terminated` (종료됨)이면 새 인스턴스가 필요합니다

## 🔧 해결 방법

### 해결 1: 보안 그룹 설정 (필수)

**AWS 콘솔:**
1. EC2 → 인스턴스 선택
2. 보안 탭 → 보안 그룹 클릭
3. 인바운드 규칙 편집
4. 규칙 추가:
   - 유형: `사용자 지정 TCP`
   - 포트: `8000`
   - 소스: `0.0.0.0/0`
5. 규칙 저장

### 해결 2: EC2 서비스 시작

```bash
# EC2 SSH 접속
ssh -i your-key.pem ubuntu@13.125.210.86

# 서비스 시작
sudo systemctl start rag-api.service
sudo systemctl enable rag-api.service

# 상태 확인
sudo systemctl status rag-api.service
```

### 해결 3: 방화벽 확인 (Ubuntu)

**EC2에서:**

```bash
# UFW 방화벽 상태 확인
sudo ufw status

# 포트 8000이 열려있는지 확인
# 열려있지 않으면:
sudo ufw allow 8000/tcp
sudo ufw reload
```

### 해결 4: 네트워크 ACL 확인

**AWS 콘솔:**
1. **VPC 콘솔** → **네트워크 ACL**
2. 인스턴스와 연결된 네트워크 ACL 확인
3. 인바운드 규칙에 포트 8000이 허용되어 있는지 확인

## ✅ 확인 체크리스트

- [ ] EC2 보안 그룹 인바운드 규칙에 포트 8000 추가 (소스: 0.0.0.0/0)
- [ ] EC2 서비스 실행 중 (`systemctl status`)
- [ ] EC2 로컬 헬스 체크 성공 (`curl localhost:8000/health`)
- [ ] 로컬 컴퓨터에서 EC2 외부 접근 성공 (`curl http://13.125.210.86:8000/health`)
- [ ] EC2 인스턴스 상태가 `running`
- [ ] UFW 방화벽이 포트 8000을 허용

## 🧪 테스트 방법

### 1. 로컬에서 EC2 테스트

```powershell
# Windows PowerShell
Invoke-WebRequest -Uri "http://13.125.210.86:8000/health" -Method GET
```

### 2. Vercel에서 다시 테스트

보안 그룹 설정 후:
1. Vercel 사이트 접속
2. 챗봇에 메시지 전송
3. 오류가 해결되었는지 확인

## 📝 추가 확인 사항

### EC2 로그 확인

```bash
# EC2에서
sudo journalctl -u rag-api.service -n 100 --no-pager
```

### 네트워크 연결 테스트

```bash
# EC2에서 외부에서 들어오는 연결 테스트
sudo netstat -tuln | grep 8000
# 또는
sudo ss -tuln | grep 8000
```

포트가 `LISTEN` 상태여야 합니다.

## 🆘 여전히 문제가 있으면

1. **EC2 인스턴스 재시작**
   ```bash
   # AWS 콘솔에서 인스턴스 재시작
   # 또는 SSH에서
   sudo reboot
   ```

2. **서비스 재시작**
   ```bash
   sudo systemctl restart rag-api.service
   ```

3. **새 보안 그룹 생성**
   - 기존 보안 그룹 대신 새 보안 그룹 생성
   - 포트 8000 규칙 추가
   - 인스턴스에 새 보안 그룹 연결
