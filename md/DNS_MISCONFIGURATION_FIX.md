# DNS 설정 오류 해결 가이드

## 🚨 문제 발견

**EC2에서 DNS 해석 결과:**
```
nslookup api.leejinhyung.shop
Address: 64.29.17.1
Address: 216.198.79.1
```

**예상 결과:**
```
Address: 43.200.176.200
```

## 🔍 원인

가비아 DNS에서 `api.leejinhyung.shop` A 레코드가 잘못 설정되어 있거나, 다른 레코드가 우선순위를 가지고 있습니다.

## 🔧 해결 방법

### 1단계: 가비아 DNS 설정 확인

**가비아 DNS 관리 페이지에서:**

1. `api.leejinhyung.shop` 레코드 확인
2. 현재 설정된 IP 주소 확인
3. **반드시 `43.200.176.200`으로 설정되어 있어야 함**

### 2단계: DNS 레코드 수정

**가비아 DNS에서:**

1. `api.leejinhyung.shop` A 레코드 찾기
2. **수정** 클릭
3. **값/위치** 필드를 `43.200.176.200`으로 변경
4. **저장** 클릭

### 3단계: 다른 레코드 확인

**가비아 DNS에서 확인:**
- `api.leejinhyung.shop`에 여러 레코드가 있는지 확인
- CNAME 레코드가 있는지 확인
- 다른 A 레코드가 있는지 확인

**잘못된 레코드가 있다면 삭제:**
- `64.29.17.1`로 설정된 레코드 삭제
- `216.198.79.1`로 설정된 레코드 삭제

### 4단계: DNS 전파 대기

DNS 변경 후 전파에는 시간이 걸립니다:
- 최소: 몇 분
- 최대: 24-48시간
- 보통: 1-2시간

### 5단계: DNS 해석 확인

**로컬 컴퓨터에서:**
```powershell
# Windows PowerShell
nslookup api.leejinhyung.shop

# 예상 결과:
# Name: api.leejinhyung.shop
# Address: 43.200.176.200
```

**EC2에서:**
```bash
nslookup api.leejinhyung.shop

# 예상 결과:
# Address: 43.200.176.200
```

## 📝 확인 체크리스트

### 가비아 DNS 설정
- [ ] `api.leejinhyung.shop` A 레코드가 `43.200.176.200`으로 설정
- [ ] 잘못된 레코드 (`64.29.17.1`, `216.198.79.1`) 삭제
- [ ] TTL 설정 확인 (1800초 권장)

### DNS 해석 확인
- [ ] 로컬에서 `nslookup api.leejinhyung.shop` 결과가 `43.200.176.200`
- [ ] EC2에서 `nslookup api.leejinhyung.shop` 결과가 `43.200.176.200`

### 테스트
- [ ] `curl http://api.leejinhyung.shop:8000/health` 성공
- [ ] Vercel에서 챗봇 테스트 성공

## ⚠️ 중요 사항

**현재 상황:**
- EC2 서비스는 정상 실행 중 ✅
- 포트 8000 리스닝 중 ✅
- 하지만 DNS가 잘못 해석되어 Vercel에서 연결 실패 ❌

**해결 후:**
- 가비아 DNS를 `43.200.176.200`으로 수정
- DNS 전파 대기
- Vercel에서 다시 테스트

## 🎯 즉시 조치

1. **가비아 DNS 관리 페이지 접속**
2. **`api.leejinhyung.shop` 레코드 확인**
3. **IP 주소를 `43.200.176.200`으로 수정**
4. **잘못된 레코드 삭제**
5. **저장 후 DNS 전파 대기**

DNS가 올바르게 설정되면 Vercel에서 정상적으로 연결될 것입니다.
