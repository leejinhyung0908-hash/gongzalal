# EC2 프로젝트 배포 위치 전략

## 📍 배포 위치 옵션 비교

### 1. `/home/ubuntu/rag` (현재 사용 중) ⭐ **권장**

**장점:**
- ✅ 사용자 권한으로 관리 가능 (sudo 불필요)
- ✅ 간단한 설정 및 배포
- ✅ 개발/테스트 환경에 적합
- ✅ 사용자별 격리 가능
- ✅ 백업 및 복원이 쉬움

**단점:**
- ❌ 홈 디렉토리는 사용자 데이터용으로 간주됨
- ❌ 프로덕션 환경에서는 덜 표준적

**권장 사용:**
- 개발/스테이징 환경
- 단일 사용자/소규모 프로젝트
- 빠른 프로토타이핑

---

### 2. `/opt/rag` ⭐⭐ **프로덕션 권장**

**장점:**
- ✅ 시스템 소프트웨어용 표준 위치
- ✅ 프로덕션 환경에 적합
- ✅ 여러 사용자가 접근 가능
- ✅ 시스템 레벨 관리 용이

**단점:**
- ❌ sudo 권한 필요
- ❌ 소유권 설정 필요

**설정 방법:**
```bash
# 디렉토리 생성 및 권한 설정
sudo mkdir -p /opt/rag
sudo chown -R ubuntu:ubuntu /opt/rag

# systemd 서비스 파일 수정
sudo nano /etc/systemd/system/rag-api.service
# WorkingDirectory=/opt/rag
# EnvironmentFile=/opt/rag/.env
```

**권장 사용:**
- 프로덕션 환경
- 여러 서비스가 공유하는 시스템
- 표준 Linux 관례 준수

---

### 3. `/srv/rag`

**장점:**
- ✅ 서비스 데이터용 표준 위치
- ✅ 웹 서버 데이터와 함께 관리 가능

**단점:**
- ❌ 주로 웹 서버 데이터용으로 사용
- ❌ FastAPI에는 덜 일반적

**권장 사용:**
- 웹 서버와 함께 운영
- 정적 파일 서빙이 필요한 경우

---

### 4. `/var/www/rag`

**장점:**
- ✅ 전통적인 웹 애플리케이션 위치
- ✅ 웹 서버와 통합 용이

**단점:**
- ❌ Apache/Nginx 전용 관례
- ❌ FastAPI에는 덜 적합

**권장 사용:**
- Nginx 리버스 프록시와 함께 사용
- 전통적인 웹 서버 환경

---

## 🎯 최종 권장사항

### CPU 기반 EC2 배포 전략

#### **옵션 A: 개발/스테이징 환경** (현재 설정 유지)
```
/home/ubuntu/rag
```
- ✅ **현재 설정 그대로 사용 권장**
- ✅ 간단하고 빠른 배포
- ✅ 사용자 권한으로 충분

#### **옵션 B: 프로덕션 환경** (표준 준수)
```
/opt/rag
```
- ✅ 시스템 표준 위치
- ✅ 프로덕션 환경에 적합
- ✅ 여러 서비스 관리 용이

---

## 🔄 현재 설정에서 `/opt/rag`로 변경하는 방법

### 1. GitHub Actions 워크플로우 수정

`.github/workflows/deploy-ec2.yml`:

```yaml
# 변경 전
APP_DIR="$HOME/rag"

# 변경 후
APP_DIR="/opt/rag"
```

### 2. systemd 서비스 파일 수정

`scripts/rag-api.service`:

```ini
[Service]
User=ubuntu
WorkingDirectory=/opt/rag
Environment="PATH=/opt/rag/venv/bin"
ExecStart=/opt/rag/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
EnvironmentFile=/opt/rag/.env
```

### 3. EC2에서 초기 설정

```bash
# 디렉토리 생성 및 권한 설정
sudo mkdir -p /opt/rag
sudo chown -R ubuntu:ubuntu /opt/rag

# 저장소 클론
cd /opt
sudo -u ubuntu git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git rag
cd rag

# 가상환경 생성
sudo -u ubuntu python3 -m venv venv
sudo -u ubuntu source venv/bin/activate
sudo -u ubuntu pip install -r backend/requirements.txt

# systemd 서비스 설정
sudo cp scripts/rag-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rag-api.service
sudo systemctl start rag-api.service
```

---

## 📊 비교 요약표

| 위치 | 권한 | 표준성 | 프로덕션 | 복잡도 | 권장도 |
|------|------|--------|----------|--------|--------|
| `/home/ubuntu/rag` | 사용자 | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ |
| `/opt/rag` | sudo 필요 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| `/srv/rag` | sudo 필요 | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| `/var/www/rag` | sudo 필요 | ⭐ | ⭐ | ⭐⭐ | ⭐ |

---

## 💡 최종 결론

### **현재 프로젝트에 대한 권장사항:**

1. **현재 설정 유지 (`/home/ubuntu/rag`)** ✅
   - 개발/스테이징 환경
   - 빠른 배포 및 테스트
   - 단일 사용자 환경
   - **CPU 기반 EC2에는 충분**

2. **프로덕션 전환 시 (`/opt/rag`)**
   - 프로덕션 환경
   - 표준 준수 필요
   - 여러 서비스 관리

### **CPU 기반 EC2 특성 고려:**

- CPU 기반 EC2는 보통 개발/테스트/소규모 프로덕션용
- `/home/ubuntu/rag`가 **가장 실용적이고 관리하기 쉬움**
- 추가 설정 없이 바로 사용 가능
- **현재 설정 그대로 사용하는 것을 권장합니다!** ✅

---

## 🔧 현재 설정 유지 시 장점

1. **간단한 배포**: GitHub Actions 워크플로우 그대로 사용
2. **권한 문제 없음**: sudo 없이 모든 작업 가능
3. **빠른 설정**: 추가 디렉토리 생성/권한 설정 불필요
4. **충분한 격리**: 사용자 홈 디렉토리 내에서 격리
5. **표준 준수**: 개발 환경에서는 일반적인 관례

**결론: CPU 기반 EC2에서는 `/home/ubuntu/rag`가 최적의 선택입니다!** 🎯
