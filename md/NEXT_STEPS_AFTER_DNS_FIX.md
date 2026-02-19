# DNS 캐시 클리어 후 다음 단계

## ✅ 현재 상태

- EC2 DNS 해석: `43.200.176.200` (정상) ✅
- EC2 서비스: 정상 실행 중 ✅
- DB 연결: `connected` ✅

## 🔍 다음 확인 사항

### 1. 로컬에서 도메인으로 실제 연결 테스트

**로컬 컴퓨터에서 (Windows PowerShell):**
```powershell
# 도메인으로 헬스 체크
curl http://api.leejinhyung.shop:8000/health

# 예상 응답:
# {"status":"ok","database":"connected"}
```

**성공하면:** 로컬에서 도메인 연결 정상 ✅

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
- 연결되어 있다면 **반드시 제거**

### 4. Vercel 재배포

환경 변수 확인 후:
- Deployments → 최신 배포 → **Redeploy**

## 🎯 Vercel에서 여전히 실패하는 경우

### 옵션 1: DNS 전파 대기 (2-4시간)

Vercel이 사용하는 DNS 서버가 아직 전파되지 않았을 수 있습니다.

### 옵션 2: 임시로 IP 직접 사용 (즉시 해결)

**Vercel 환경 변수:**
```
NEXT_PUBLIC_API_URL=http://43.200.176.200:8000
```

**장점:**
- DNS 전파를 기다리지 않음
- 즉시 작동

**단점:**
- IP가 변경되면 수동 업데이트 필요

## 📝 체크리스트

### 로컬 테스트
- [ ] `curl http://api.leejinhyung.shop:8000/health` 성공
- [ ] 응답: `{"status":"ok","database":"connected"}`

### Vercel 설정
- [ ] 환경 변수 `NEXT_PUBLIC_API_URL=http://api.leejinhyung.shop:8000` 설정
- [ ] Vercel 프로젝트에 `api.leejinhyung.shop` 도메인 연결 안 됨
- [ ] Vercel 재배포 완료

### 테스트
- [ ] Vercel 배포된 사이트에서 챗봇 테스트
- [ ] 성공하면 완료 ✅

## 🚀 권장 순서

1. **로컬에서 도메인으로 테스트**
   ```powershell
   curl http://api.leejinhyung.shop:8000/health
   ```

2. **Vercel 환경 변수 확인 및 재배포**

3. **Vercel에서 테스트**
   - 성공하면 완료 ✅
   - 실패하면 임시로 IP 직접 사용

4. **2-4시간 후 도메인으로 다시 변경** (DNS 전파 완료 후)

