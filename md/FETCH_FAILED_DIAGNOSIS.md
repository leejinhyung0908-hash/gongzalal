# fetch failed 오류 진단 가이드

## 🚨 오류 분석

**오류 메시지:**
```
fetch failed
TypeError
requestUrl: http://api.leejinhyung.shop:8000/api/chat
backendUrl: http://api.leejinhyung.shop:8000
```

**의미:**
- Vercel에서 `api.leejinhyung.shop:8000`으로 연결을 시도했지만 실패
- 네트워크 레벨에서 연결이 차단되거나 서버가 응답하지 않음

## 🔍 가능한 원인

### 1. EC2 서비스가 실행되지 않음 (가장 가능성 높음)

**확인 방법 (EC2 SSH 접속 후):**
```bash
# 서비스 상태 확인
sudo systemctl status rag-api.service

# 실행 중이 아니면
sudo systemctl start rag-api.service
```

### 2. EC2가 포트 8000에서 리스닝하지 않음

**확인 방법:**
```bash
# 포트 리스닝 확인
sudo ss -tuln | grep 8000

# 예상 결과 (정상):
tcp   LISTEN 0  2048  0.0.0.0:8000  0.0.0.0:*

# 결과가 없으면 서비스가 포트 8000에서 실행되지 않음
```

### 3. DNS 해석 문제

**로컬에서 확인:**
```powershell
# Windows PowerShell
nslookup api.leejinhyung.shop

# 예상 결과:
# Name: api.leejinhyung.shop
# Address: 43.200.176.200
```

**문제가 있다면:**
- 가비아 DNS 설정 확인
- DNS 전파 대기

### 4. EC2 IP 주소 변경

EC2 인스턴스를 재시작하면 퍼블릭 IP가 변경될 수 있습니다.

**확인 방법 (EC2에서):**
```bash
curl http://169.254.169.254/latest/meta-data/public-ipv4
```

**가비아 DNS와 일치하는지 확인:**
- 가비아 DNS: `api.leejinhyung.shop` → `43.200.176.200`
- EC2 실제 IP와 일치해야 함

### 5. 네트워크 타임아웃

Vercel에서 EC2로의 연결이 타임아웃될 수 있습니다.

## 🔧 해결 방법

### 즉시 확인할 순서

#### 1단계: EC2 서비스 상태 확인

**EC2 SSH 접속 후:**
```bash
# 서비스 상태
sudo systemctl status rag-api.service

# 포트 리스닝
sudo ss -tuln | grep 8000

# 헬스 체크
curl http://localhost:8000/health
```

**예상 응답:**
```json
{"status":"ok","database":"connected"}
```

#### 2단계: 로컬에서 직접 테스트

**로컬 컴퓨터에서:**
```powershell
# EC2 IP로 직접 테스트
curl http://43.200.176.200:8000/health

# 도메인으로 테스트
curl http://api.leejinhyung.shop:8000/health
```

**성공하면:** EC2는 정상, Vercel 네트워크 문제 가능
**실패하면:** EC2 서비스 문제

#### 3단계: EC2 서비스 재시작

**EC2에서:**
```bash
# 서비스 재시작
sudo systemctl restart rag-api.service

# 상태 확인
sudo systemctl status rag-api.service

# 로그 확인
sudo journalctl -u rag-api.service -n 50 --no-pager
```

#### 4단계: EC2 보안 그룹 재확인

**AWS 콘솔:**
- EC2 → 인스턴스 선택
- 보안 탭 → 보안 그룹
- 인바운드 규칙에서 포트 8000 확인
- 소스가 `0.0.0.0/0`인지 확인

## 📝 체크리스트

### EC2 확인
- [ ] 서비스가 실행 중인지 (`sudo systemctl status rag-api.service`)
- [ ] 포트 8000에서 리스닝 중인지 (`sudo ss -tuln | grep 8000`)
- [ ] 로컬 헬스 체크 성공 (`curl http://localhost:8000/health`)
- [ ] EC2 IP가 가비아 DNS와 일치하는지

### 네트워크 확인
- [ ] 로컬에서 EC2 IP로 직접 접근 가능한지
- [ ] 로컬에서 도메인으로 접근 가능한지
- [ ] DNS 해석이 올바른지 (`nslookup api.leejinhyung.shop`)

### Vercel 확인
- [ ] 환경 변수 `NEXT_PUBLIC_API_URL=http://api.leejinhyung.shop:8000` 설정
- [ ] Vercel 프로젝트에 `api.leejinhyung.shop` 도메인이 연결되어 있지 않은지
- [ ] Vercel 재배포 완료

## 🎯 가장 가능성 높은 원인

1. **EC2 서비스가 실행되지 않음** (60%)
2. **EC2가 포트 8000에서 리스닝하지 않음** (30%)
3. **EC2 IP 주소 변경** (10%)

## 🚀 빠른 해결

**EC2 SSH 접속 후 다음 명령어 실행:**
```bash
# 1. 서비스 상태 확인 및 시작
sudo systemctl status rag-api.service
sudo systemctl start rag-api.service

# 2. 포트 확인
sudo ss -tuln | grep 8000

# 3. 헬스 체크
curl http://localhost:8000/health

# 4. 로그 확인 (오류 확인)
sudo journalctl -u rag-api.service -n 50 --no-pager
```

이 결과를 알려주시면 더 정확한 진단이 가능합니다.
