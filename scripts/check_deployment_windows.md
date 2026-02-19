# Windows에서 EC2 배포 확인하기

## 1. EC2에 SSH 접속하기

### 방법 1: PowerShell에서 SSH 사용

```powershell
# SSH 키 파일 경로 확인 (GitHub Secrets에 저장된 키)
# 보통 ~/.ssh/ 디렉토리에 저장되어 있음

# EC2에 접속
ssh -i ~/.ssh/ec2_key.pem ubuntu@YOUR_EC2_IP

# 또는 절대 경로 사용
ssh -i C:\Users\hi\.ssh\ec2_key.pem ubuntu@YOUR_EC2_IP
```

### 방법 2: PuTTY 사용 (GUI)

1. PuTTY 다운로드: https://www.putty.org/
2. PuTTYgen으로 `.pem` 파일을 `.ppk`로 변환
3. PuTTY에서 EC2 IP와 변환된 키로 접속

## 2. EC2 접속 후 확인 명령어

```bash
# 서비스 상태 확인
sudo systemctl status rag-api.service

# 서비스 로그 확인
sudo journalctl -u rag-api.service -n 50

# 헬스 체크
curl http://localhost:8000/health

# API 문서 확인
curl http://localhost:8000/docs

# 프로세스 확인
ps aux | grep uvicorn

# 포트 확인
sudo netstat -tlnp | grep 8000
```

## 3. 외부에서 확인 (Windows 브라우저)

브라우저에서 다음 URL 접속:

```
http://YOUR_EC2_IP:8000/docs
http://YOUR_EC2_IP:8000/health
```

## 4. PowerShell에서 직접 API 테스트

```powershell
# 헬스 체크
Invoke-WebRequest -Uri "http://YOUR_EC2_IP:8000/health" -Method Get

# 또는 curl 사용 (Windows 10+)
curl http://YOUR_EC2_IP:8000/health
```

## 5. EC2 IP 확인 방법

1. AWS 콘솔 → EC2 → 인스턴스 선택
2. Public IPv4 address 확인
3. 또는 GitHub Secrets의 `EC2_HOST` 값 확인

## 6. SSH 키 파일 위치

GitHub Actions에서 사용하는 키는:
- GitHub Secrets에 저장된 `EC2_SSH_KEY`
- 로컬에서는 AWS에서 다운로드한 `.pem` 파일 사용

## 7. 문제 해결

### SSH 접속 실패 시:
1. 보안 그룹에서 SSH (포트 22) 허용 확인
2. 키 파일 권한 확인 (Windows에서는 보통 문제 없음)
3. EC2 인스턴스가 실행 중인지 확인

### 서비스가 실행되지 않을 때:
```bash
# EC2에서 실행
sudo systemctl restart rag-api.service
sudo journalctl -u rag-api.service -n 100
```
