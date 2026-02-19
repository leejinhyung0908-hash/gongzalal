# 가비아 프록시 연동 가이드

## 현재 상태

- DNS 레코드: `api.leejinhyung.shop` → `43.200.176.200` (EC2 IP)
- EC2 백엔드: 포트 8000에서 실행 중

## 가비아 프록시 연동 방법

### 옵션 1: 포트 번호 포함 (가장 간단)

**Vercel 환경 변수 설정:**
```
NEXT_PUBLIC_API_URL=https://api.leejinhyung.shop:8000
```

**장점:**
- 추가 설정 불필요
- 즉시 사용 가능
- 비용 없음

**단점:**
- URL에 포트 번호 포함 (`:8000`)

### 옵션 2: 가비아 포트 포워딩 (가능한 경우)

가비아에서 포트 포워딩 기능을 제공하는 경우:

1. **가비아 DNS 설정에서:**
   - `api.leejinhyung.shop` 레코드 수정
   - 포트 포워딩 설정: `80 → 8000` 또는 `443 → 8000`

2. **Vercel 환경 변수 설정:**
   ```
   NEXT_PUBLIC_API_URL=https://api.leejinhyung.shop
   ```

**주의:** 가비아에서 포트 포워딩 기능이 유료 서비스일 수 있습니다.

### 옵션 3: EC2에서 포트 80으로 변경 (권한 필요)

EC2에서 FastAPI를 포트 80에서 실행하려면 root 권한이 필요합니다.

**EC2에서 설정:**
```bash
# systemd 서비스 파일 수정
sudo nano /etc/systemd/system/rag-api.service
```

**변경 내용:**
```ini
ExecStart=/home/ubuntu/rag/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 80
```

**주의:** 포트 80은 root 권한이 필요하므로 `sudo`로 실행해야 합니다.

## 추천 방법

**현재 상황에서는 옵션 1을 추천합니다:**
- 추가 비용 없음
- 즉시 사용 가능
- 설정이 간단함

## Vercel 환경 변수 설정

1. **Vercel 대시보드** → **프로젝트 선택** → **Settings** → **Environment Variables**

2. **환경 변수 추가/수정:**
   ```
   Name: NEXT_PUBLIC_API_URL
   Value: https://api.leejinhyung.shop:8000
   Environment: Production, Preview, Development (모두 선택)
   ```

3. **저장 후 재배포:**
   - **Deployments** → 최신 배포 → **Redeploy**

## EC2 보안 그룹 확인

EC2 보안 그룹에서 포트 8000이 열려있는지 확인:

**AWS 콘솔:**
1. EC2 → 인스턴스 선택
2. 보안 탭 → 보안 그룹 클릭
3. 인바운드 규칙 확인:
   - 포트 `8000`이 있는지
   - 소스가 `0.0.0.0/0`인지

## 테스트

**로컬에서 테스트:**
```bash
curl https://api.leejinhyung.shop:8000/health
```

**예상 응답:**
```json
{"status":"healthy","database":"connected"}
```

## 문제 해결

### SSL 인증서 오류

포트 8000에서 HTTPS를 사용하려면 EC2에 SSL 인증서가 필요합니다.
HTTP를 사용하는 경우:
```
NEXT_PUBLIC_API_URL=http://api.leejinhyung.shop:8000
```

### CORS 오류

EC2 `.env` 파일에서 CORS 설정 확인:
```env
CORS_ORIGINS=https://www.leejinhyung.shop,https://leejinhyung.shop
```

서비스 재시작:
```bash
sudo systemctl restart rag-api.service
```
