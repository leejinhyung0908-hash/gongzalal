# EC2 연결 타임아웃 빠른 해결 체크리스트

## 🚨 현재 문제

Vercel에서 EC2로 연결 타임아웃 발생:
```
ConnectTimeoutError: Connect Timeout Error
(attempted address: 13.125.210.86:8000, timeout: 10000ms)
```

## ✅ 즉시 확인할 5가지

### 1. EC2 서비스 실행 확인

EC2 SSH 접속 후:
```bash
sudo systemctl status rag-api.service
```

**실행 중이 아니면:**
```bash
sudo systemctl start rag-api.service
```

### 2. 포트 리스닝 확인

```bash
sudo ss -tuln | grep 8000
```

**예상 결과:**
```
tcp   LISTEN 0  2048  0.0.0.0:8000  0.0.0.0:*
```

### 3. EC2 보안 그룹 확인

**AWS 콘솔:**
1. EC2 → 인스턴스 선택
2. 보안 탭 → 보안 그룹 클릭
3. 인바운드 규칙 확인:
   - 포트 `8000`이 있는지
   - 소스가 `0.0.0.0/0`인지

**없으면 추가:**
- 유형: `사용자 지정 TCP`
- 포트: `8000`
- 소스: `0.0.0.0/0`

### 4. EC2 퍼블릭 IP 확인

```bash
curl http://169.254.169.254/latest/meta-data/public-ipv4
```

**Vercel 환경 변수와 일치하는지 확인:**
- Vercel 대시보드 → Settings → Environment Variables
- `BACKEND_URL` 값 확인

### 5. Vercel 환경 변수 및 Redeploy

**Vercel 대시보드:**
1. Settings → Environment Variables
2. `BACKEND_URL` 확인: `http://13.125.210.86:8000`
3. Deployments → 최신 배포 → Redeploy

## 🔧 빠른 해결 순서

1. **EC2 서비스 확인 및 시작**
2. **포트 리스닝 확인**
3. **보안 그룹 확인 및 수정**
4. **Vercel 환경 변수 확인**
5. **Vercel Redeploy**

## 📝 확인 명령어 (EC2에서)

```bash
# 1. 서비스 상태
sudo systemctl status rag-api.service

# 2. 포트 리스닝
sudo ss -tuln | grep 8000

# 3. 퍼블릭 IP
curl http://169.254.169.254/latest/meta-data/public-ipv4

# 4. 로컬 헬스 체크
curl http://localhost:8000/health
```

## 🆘 여전히 문제가 있으면

1. **EC2 인스턴스 재시작**
2. **새 보안 그룹 생성 및 연결**
3. **Elastic IP 할당** (고정 IP 사용)
