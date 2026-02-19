# Vercel 연결 타임아웃 해결 가이드

## 🔍 현재 오류

**Vercel 함수 로그:**
```
ConnectTimeoutError: Connect Timeout Error
(attempted address: 13.125.210.86:8000, timeout: 10000ms)
```

**의미:**
- Vercel에서 EC2(`13.125.210.86:8000`)로 연결할 수 없음
- 10초 타임아웃 내에 연결 실패

## 🚨 가능한 원인

### 1. EC2 보안 그룹 설정 문제

보안 그룹에서 포트 8000이 열려있지만, Vercel의 IP가 차단되었을 수 있습니다.

**확인 방법:**
- AWS 콘솔에서 보안 그룹 인바운드 규칙 확인
- 포트 8000이 `0.0.0.0/0`에서 허용되어 있는지 확인

### 2. EC2 인스턴스 퍼블릭 IP 변경

EC2 인스턴스를 재시작하면 퍼블릭 IP가 변경될 수 있습니다.

**확인 방법:**
```bash
# EC2에서 현재 퍼블릭 IP 확인
curl http://169.254.169.254/latest/meta-data/public-ipv4
```

### 3. EC2 서비스가 실행되지 않음

서비스가 중지되었을 수 있습니다.

**확인 방법:**
```bash
# EC2에서
sudo systemctl status rag-api.service
```

### 4. 네트워크 ACL 문제

VPC의 네트워크 ACL에서 포트 8000이 차단되었을 수 있습니다.

## 🔧 해결 방법

### 해결 1: EC2 보안 그룹 재확인 및 수정

**AWS 콘솔에서:**

1. **EC2 콘솔** → **인스턴스** → 인스턴스 선택
2. **보안** 탭 → **보안 그룹** 클릭
3. **인바운드 규칙** 확인:
   - 포트 `8000`이 있는지 확인
   - 소스가 `0.0.0.0/0`인지 확인

**규칙이 없거나 잘못되었으면:**

1. **인바운드 규칙 편집** 클릭
2. **규칙 추가** 클릭
3. 다음 설정:
   - **유형**: `사용자 지정 TCP`
   - **포트**: `8000`
   - **소스**: `0.0.0.0/0` (모든 IPv4 주소)
   - **설명**: `Vercel API access`
4. **규칙 저장** 클릭

### 해결 2: EC2 서비스 상태 확인

EC2 SSH 접속 후:
```bash
# 서비스 상태 확인
sudo systemctl status rag-api.service

# 실행 중이 아니면 시작
sudo systemctl start rag-api.service

# 헬스 체크
curl http://localhost:8000/health
```

### 해결 3: EC2 퍼블릭 IP 확인

EC2에서:
```bash
# 현재 퍼블릭 IP 확인
curl http://169.254.169.254/latest/meta-data/public-ipv4
```

**Vercel 환경 변수 확인:**
- Vercel 대시보드 → Settings → Environment Variables
- `BACKEND_URL`이 올바른 IP로 설정되어 있는지 확인
- IP가 변경되었다면 업데이트 후 Redeploy

### 해결 4: 포트 리스닝 확인

EC2에서:
```bash
# 포트 8000이 리스닝 중인지 확인
sudo ss -tuln | grep 8000

# 예상 결과:
# tcp   LISTEN 0  2048  0.0.0.0:8000  0.0.0.0:*
```

### 해결 5: 네트워크 ACL 확인

**AWS 콘솔에서:**

1. **VPC 콘솔** → **네트워크 ACL**
2. EC2 인스턴스와 연결된 네트워크 ACL 확인
3. 인바운드 규칙에 포트 8000이 허용되어 있는지 확인

## ✅ 확인 체크리스트

- [ ] EC2 보안 그룹 인바운드 규칙에 포트 8000 추가 (소스: 0.0.0.0/0)
- [ ] EC2 서비스 실행 중 확인
- [ ] EC2 포트 8000 리스닝 확인
- [ ] EC2 퍼블릭 IP 확인
- [ ] Vercel 환경 변수 `BACKEND_URL` 확인 및 업데이트
- [ ] Vercel Redeploy 실행

## 🧪 단계별 진단

### Step 1: EC2 상태 확인

```bash
# EC2 SSH 접속
ssh -i "kroaddy.pem" ubuntu@ec2-3-34-47-44.ap-northeast-2.compute.amazonaws.com

# 서비스 상태
sudo systemctl status rag-api.service

# 포트 리스닝
sudo ss -tuln | grep 8000

# 퍼블릭 IP 확인
curl http://169.254.169.254/latest/meta-data/public-ipv4
```

### Step 2: 보안 그룹 확인

AWS 콘솔에서 보안 그룹 인바운드 규칙 확인

### Step 3: Vercel 환경 변수 확인

Vercel 대시보드 → Settings → Environment Variables → `BACKEND_URL` 확인

### Step 4: Vercel Redeploy

환경 변수 수정 후 반드시 Redeploy

## 🆘 여전히 문제가 있으면

1. **EC2 인스턴스 재시작**
   - AWS 콘솔에서 인스턴스 재시작
   - 퍼블릭 IP가 변경될 수 있으므로 확인 필요

2. **새 보안 그룹 생성**
   - 기존 보안 그룹 대신 새 보안 그룹 생성
   - 포트 8000 규칙 추가
   - 인스턴스에 새 보안 그룹 연결

3. **Elastic IP 사용**
   - EC2에 Elastic IP 할당
   - 고정 IP 사용으로 IP 변경 문제 해결
