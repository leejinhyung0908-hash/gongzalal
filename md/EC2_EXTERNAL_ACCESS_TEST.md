# EC2 외부 접근 테스트 가이드

## ✅ EC2 서비스 상태 (정상)

확인 결과:
- ✅ 서비스 실행 중: `active (running)`
- ✅ 포트 8000 리스닝: `0.0.0.0:8000`
- ✅ 로컬 헬스 체크 성공: `{"status":"ok","database":"error"}`

## 🔍 다음 확인 사항

### 1. 외부에서 EC2 IP로 직접 접근 테스트

**로컬 컴퓨터에서 (Windows PowerShell):**
```powershell
# EC2 IP로 직접 테스트
curl http://43.200.176.200:8000/health

# 또는
Invoke-WebRequest -Uri "http://43.200.176.200:8000/health" -Method GET
```

**예상 응답:**
```json
{"status":"ok","database":"error"}
```

**실패하면:**
- EC2 보안 그룹 문제 (포트 8000이 외부에서 차단됨)
- 네트워크 ACL 문제

### 2. 도메인으로 접근 테스트

**로컬 컴퓨터에서:**
```powershell
# 도메인으로 테스트
curl http://api.leejinhyung.shop:8000/health

# 또는
Invoke-WebRequest -Uri "http://api.leejinhyung.shop:8000/health" -Method GET
```

**성공하면:** DNS와 네트워크 정상
**실패하면:** DNS 문제 또는 가비아 프록시 문제

### 3. DNS 해석 확인

**로컬 컴퓨터에서:**
```powershell
nslookup api.leejinhyung.shop
```

**예상 결과:**
```
Name: api.leejinhyung.shop
Address: 43.200.176.200
```

### 4. EC2에서 외부 접근 로그 확인

**EC2 SSH 접속 후:**
```bash
# 실시간 로그 확인 (외부 요청이 오는지 확인)
sudo journalctl -u rag-api.service -f
```

그 다음 로컬에서 `curl http://43.200.176.200:8000/health` 실행하고, EC2 로그에 요청이 나타나는지 확인

## 🚨 가능한 문제

### 문제 1: EC2 보안 그룹이 외부 접근을 차단

**확인:**
- AWS 콘솔 → EC2 → 인스턴스 → 보안 그룹
- 인바운드 규칙에서 포트 8000 확인
- 소스가 `0.0.0.0/0`인지 확인

### 문제 2: Vercel에서 EC2로의 네트워크 경로 문제

**증상:**
- 로컬에서는 접근 가능
- Vercel에서는 `fetch failed`

**가능한 원인:**
- Vercel의 네트워크 정책
- 지역별 IP 차단
- Vercel 서버리스 함수의 네트워크 제한

### 문제 3: DNS 전파 지연

**증상:**
- `nslookup` 결과가 다름
- 일부 지역에서만 접근 불가

**해결:**
- DNS 전파 대기 (보통 몇 분~몇 시간)

## 📝 다음 단계

1. **로컬에서 EC2 IP로 직접 테스트**
2. **로컬에서 도메인으로 테스트**
3. **DNS 해석 확인**
4. **결과에 따라 문제 해결**
