# DNS 전파 및 캐시 문제 해결

## ✅ 가비아 DNS 설정 확인 완료

가비아 DNS 설정은 **올바르게** 되어 있습니다:
- `api.leejinhyung.shop` → `43.200.176.200` ✅

## 🔍 문제 원인

EC2에서 `nslookup` 결과가 다른 IP로 나오는 이유:
1. **DNS 전파 지연**: DNS 변경사항이 전 세계 DNS 서버에 전파되는데 시간이 걸림
2. **DNS 캐시**: 로컬 DNS 서버나 EC2의 DNS 캐시에 이전 값이 남아있음
3. **TTL 설정**: TTL이 1800초(30분)로 설정되어 있어 캐시가 오래 유지됨

## 🔧 해결 방법

### 방법 1: DNS 캐시 클리어 (EC2에서)

**EC2 SSH 접속 후:**
```bash
# systemd-resolved 캐시 클리어
sudo systemd-resolve --flush-caches

# 또는
sudo resolvectl flush-caches

# 다시 확인
nslookup api.leejinhyung.shop
```

### 방법 2: 다른 DNS 서버 사용

**EC2에서:**
```bash
# Google DNS 사용
nslookup api.leejinhyung.shop 8.8.8.8

# Cloudflare DNS 사용
nslookup api.leejinhyung.shop 1.1.1.1
```

**예상 결과:**
```
Name: api.leejinhyung.shop
Address: 43.200.176.200
```

### 방법 3: DNS 전파 대기

DNS 변경 후 전파 시간:
- **최소**: 몇 분
- **보통**: 1-2시간
- **최대**: 24-48시간 (TTL에 따라)

가비아에서 최근 업데이트가 `2025-12-23 15:18:06`이므로, 아직 전파 중일 수 있습니다.

### 방법 4: 로컬에서 확인

**로컬 컴퓨터에서 (Windows PowerShell):**
```powershell
# DNS 캐시 클리어
ipconfig /flushdns

# 확인
nslookup api.leejinhyung.shop

# Google DNS 사용
nslookup api.leejinhyung.shop 8.8.8.8
```

## 📝 확인 체크리스트

### 가비아 DNS 설정
- [x] `api.leejinhyung.shop` → `43.200.176.200` ✅
- [x] TTL: 1800초 ✅
- [x] 최근 업데이트: 2025-12-23 15:18:06 ✅

### DNS 해석 확인
- [ ] EC2에서 `nslookup api.leejinhyung.shop 8.8.8.8` 결과가 `43.200.176.200`
- [ ] 로컬에서 `nslookup api.leejinhyung.shop` 결과가 `43.200.176.200`

### 테스트
- [ ] `curl http://api.leejinhyung.shop:8000/health` 성공
- [ ] Vercel에서 챗봇 테스트 성공

## 🎯 즉시 조치

### 1. EC2에서 DNS 캐시 클리어
```bash
sudo systemd-resolve --flush-caches
# 또는
sudo resolvectl flush-caches
```

### 2. Google DNS로 확인
```bash
nslookup api.leejinhyung.shop 8.8.8.8
```

### 3. 로컬에서도 확인
```powershell
ipconfig /flushdns
nslookup api.leejinhyung.shop 8.8.8.8
```

## ⚠️ 중요 사항

**가비아 DNS 설정은 올바릅니다!**

문제는 DNS 전파/캐시입니다. 다음을 시도하세요:
1. DNS 캐시 클리어
2. 다른 DNS 서버(8.8.8.8)로 확인
3. DNS 전파 대기 (1-2시간)

가비아 설정이 올바르므로, DNS 전파가 완료되면 Vercel에서 정상적으로 연결될 것입니다.
