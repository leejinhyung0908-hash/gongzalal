# 실제 연결 테스트 가이드

## 🎯 중요한 것

Google DNS 체크는 **참고용**일 뿐입니다. 실제로 중요한 것은:

1. **로컬에서 실제로 연결이 되는지**
2. **Vercel 환경 변수가 올바른지**
3. **실제 요청이 성공하는지**

## ✅ 확인해야 할 것

### 1. 로컬에서 실제 연결 테스트

**Windows PowerShell:**
```powershell
# 도메인으로 직접 테스트
curl http://api.leejinhyung.shop:8000/health

# 또는
Invoke-WebRequest -Uri "http://api.leejinhyung.shop:8000/health" -Method GET
```

**성공하면:**
```json
{"status":"ok","database":"connected"}
```

**이것이 성공하면** → 로컬 DNS가 올바르게 작동하고, 실제 연결도 가능합니다.

### 2. Vercel 환경 변수 확인

**Vercel 대시보드:**
- Settings → Environment Variables
- `NEXT_PUBLIC_API_URL` 확인:
  ```
  http://api.leejinhyung.shop:8000
  ```

### 3. Vercel 프로젝트 도메인 확인

**Vercel 대시보드:**
- Settings → Domains
- `api.leejinhyung.shop`이 **연결되어 있지 않은지** 확인
- 연결되어 있다면 **반드시 제거** (백엔드용이므로)

## 🔍 Google DNS는 왜 체크했나?

Google DNS(8.8.8.8)는:
- Google Cloud와 **무관한** 공개 DNS 서비스
- 전 세계에서 사용되는 무료 DNS 서버
- DNS 전파 상태를 확인하는 **참고용**

**하지만 필수는 아닙니다!**

## 🎯 실제 해결 방법

### 방법 1: 로컬에서 연결 테스트

```powershell
curl http://api.leejinhyung.shop:8000/health
```

**성공하면:**
- 로컬 DNS는 정상 ✅
- 실제 연결도 가능 ✅
- Vercel도 작동할 가능성 높음

**실패하면:**
- 다른 문제가 있을 수 있음
- EC2 보안 그룹 확인 필요

### 방법 2: Vercel 환경 변수 확인

Vercel이 어떤 DNS를 사용하는지는 알 수 없지만, 환경 변수가 올바르게 설정되어 있는지 확인:

```
NEXT_PUBLIC_API_URL=http://api.leejinhyung.shop:8000
```

### 방법 3: Vercel 재배포

환경 변수 수정 후 반드시 재배포:
- Deployments → 최신 배포 → Redeploy

## 📝 체크리스트

### 실제 연결 테스트
- [ ] 로컬에서 `curl http://api.leejinhyung.shop:8000/health` 성공
- [ ] Vercel 환경 변수 올바르게 설정
- [ ] Vercel 프로젝트에 `api.leejinhyung.shop` 도메인 연결 안 됨
- [ ] Vercel 재배포 완료

### Google DNS 체크
- [ ] **필수 아님** - 참고용일 뿐

## ⚠️ 중요 사항

**Google DNS 체크는 선택사항입니다.**

실제로 중요한 것은:
1. 로컬에서 실제 연결이 되는지
2. Vercel 환경 변수가 올바른지
3. Vercel에서 실제로 작동하는지

로컬에서 `curl http://api.leejinhyung.shop:8000/health`가 성공하면, Vercel도 작동할 가능성이 높습니다.
