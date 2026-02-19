# Vercel 도메인 충돌 해결 가이드

## 🚨 문제

**오류 메시지:**
```
The deployment could not be found on Vercel.
DEPLOYMENT_NOT_FOUND
```

**원인:**
- Vercel이 `api.leejinhyung.shop` 요청을 자신의 배포로 인식하려고 시도
- `api.leejinhyung.shop`이 Vercel 프로젝트에 연결되어 있거나
- DNS가 Vercel로 라우팅되고 있음

## 🔧 해결 방법

### 방법 1: Vercel 프로젝트에서 도메인 제거 (권장)

**Vercel 대시보드에서:**

1. **프로젝트 선택** → **Settings** → **Domains**
2. `api.leejinhyung.shop` 도메인이 연결되어 있는지 확인
3. **연결되어 있다면 제거:**
   - 도메인 옆 **⋯** (점 3개) 클릭
   - **Remove** 클릭

**중요:** `api.leejinhyung.shop`은 백엔드(EC2)용이므로 Vercel 프로젝트에 연결하면 안 됩니다.

### 방법 2: HTTP 사용 (SSL 인증서 없이)

포트 8000에서 HTTPS를 사용하려면 SSL 인증서가 필요합니다. HTTP를 사용하도록 변경:

**Vercel 환경 변수:**
```
NEXT_PUBLIC_API_URL=http://api.leejinhyung.shop:8000
```

**주의:**
- HTTP는 암호화되지 않으므로 프로덕션에서는 권장하지 않음
- 하지만 테스트/개발 환경에서는 사용 가능

### 방법 3: 다른 서브도메인 사용

가비아 DNS에서 새로운 서브도메인 추가:

1. **가비아 DNS 설정:**
   - 새 레코드 추가: `backend.leejinhyung.shop` → `43.200.176.200` (A 레코드)

2. **Vercel 환경 변수:**
   ```
   NEXT_PUBLIC_API_URL=http://backend.leejinhyung.shop:8000
   ```

## ✅ 확인 체크리스트

### 1. Vercel 도메인 설정 확인
- [ ] Vercel 프로젝트 → Settings → Domains
- [ ] `api.leejinhyung.shop`이 연결되어 있지 않은지 확인
- [ ] 연결되어 있다면 제거

### 2. 가비아 DNS 설정 확인
- [ ] `api.leejinhyung.shop` A 레코드가 `43.200.176.200`으로 설정
- [ ] TTL이 적절한지 확인 (1800초 권장)

### 3. Vercel 환경 변수 확인
- [ ] `NEXT_PUBLIC_API_URL`이 올바르게 설정되어 있는지
- [ ] HTTP 사용 시: `http://api.leejinhyung.shop:8000`
- [ ] HTTPS 사용 시: `https://api.leejinhyung.shop:8000` (SSL 인증서 필요)

### 4. DNS 전파 확인
```bash
# Windows PowerShell
nslookup api.leejinhyung.shop

# 예상 결과
Name: api.leejinhyung.shop
Address: 43.200.176.200
```

## 🧪 테스트

### 1. DNS 해석 확인
```bash
nslookup api.leejinhyung.shop
```

### 2. 직접 접근 테스트
```bash
# Windows PowerShell
curl http://api.leejinhyung.shop:8000/health

# 예상 응답
{"status":"healthy","database":"connected"}
```

### 3. Vercel에서 테스트
1. Vercel 배포된 사이트 접속
2. 브라우저 개발자 도구 (F12) → Network 탭
3. 챗봇에 메시지 전송
4. `/api/chat` 요청이 `api.leejinhyung.shop:8000`으로 가는지 확인

## 📝 단계별 해결 순서

1. **Vercel 프로젝트에서 `api.leejinhyung.shop` 도메인 제거**
2. **Vercel 환경 변수 설정:**
   ```
   NEXT_PUBLIC_API_URL=http://api.leejinhyung.shop:8000
   ```
3. **Vercel 재배포**
4. **테스트**

## ⚠️ 주의사항

- `api.leejinhyung.shop`은 **백엔드(EC2)용**이므로 Vercel 프로젝트에 연결하면 안 됩니다
- `www.leejinhyung.shop`만 Vercel 프로젝트에 연결되어야 합니다
- HTTP는 암호화되지 않으므로 프로덕션에서는 HTTPS + SSL 인증서 사용 권장
