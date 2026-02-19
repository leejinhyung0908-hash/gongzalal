# EC2 로컬 LLM 오류 해결 가이드

## 🔍 문제 분석

**오류 발생 모드:**
- ❌ `rag_local` (RAG + 로컬 LLM)
- ❌ `local` (로컬 LLM만)
- ❌ `qlora` (QLoRA)

**정상 작동 모드:**
- ✅ `rag` (RAG만)
- ✅ `openai` (OpenAI만)
- ✅ `rag_openai` (RAG + OpenAI)

## 🚨 가능한 원인

### 1. 모델 파일이 EC2에 없음 (가장 가능성 높음)

로컬 LLM 모드들은 `backend/model/midm` 경로에서 모델을 찾습니다.

**확인 방법:**
```bash
# EC2 SSH 접속
ssh -i your-key.pem ubuntu@13.125.210.86

# 모델 경로 확인
cd /home/ubuntu/rag
ls -la backend/model/

# midm 모델 확인
ls -la backend/model/midm/
```

**예상 결과:**
- 모델 파일이 없으면: `No such file or directory`
- 모델 파일이 있으면: `config.json`, `pytorch_model.bin` 등이 보임

### 2. 메모리 부족

CPU 전용 EC2에서 대형 모델 로드 시 메모리 부족 가능.

**확인 방법:**
```bash
# 메모리 사용량 확인
free -h

# 디스크 공간 확인
df -h
```

### 3. 모델 로딩 실패

EC2 로그에서 구체적인 오류 확인 필요.

**확인 방법:**
```bash
# EC2에서 최근 로그 확인
sudo journalctl -u rag-api.service -n 200 --no-pager | grep -i "model\|llm\|error"
```

## 🔧 해결 방법

### 해결 1: 모델 파일 확인 및 업로드

**EC2에서 모델 경로 확인:**
```bash
cd /home/ubuntu/rag
ls -la backend/model/midm/
```

**모델이 없으면:**

1. **로컬에서 모델 확인:**
   ```bash
   # 로컬 컴퓨터에서
   ls backend/model/midm/
   ```

2. **모델을 EC2에 업로드:**
   ```bash
   # 로컬 컴퓨터에서 (Windows PowerShell)
   scp -i your-key.pem -r backend/model ubuntu@13.125.210.86:/home/ubuntu/rag/backend/
   ```

3. **권한 확인:**
   ```bash
   # EC2에서
   chmod -R 755 /home/ubuntu/rag/backend/model
   ```

### 해결 2: EC2 로그 확인

**구체적인 오류 메시지 확인:**
```bash
# EC2에서
sudo journalctl -u rag-api.service -n 500 --no-pager

# 또는 실시간 로그
sudo journalctl -u rag-api.service -f
```

**확인할 오류:**
- `FileNotFoundError`: 모델 파일을 찾을 수 없음
- `OutOfMemoryError`: 메모리 부족
- `RuntimeError`: 모델 로딩 실패
- `CUDA error`: GPU 관련 오류 (CPU 전용이므로 발생하면 안 됨)

### 해결 3: 모델 경로 설정 확인

**EC2 .env 파일 확인:**
```bash
cd /home/ubuntu/rag
cat .env | grep MODEL_BASE_PATH
```

**기본값 확인:**
- `MODEL_BASE_PATH`가 설정되지 않으면 기본값: `./model`
- 실제 경로: `/home/ubuntu/rag/backend/model`

**필요시 수정:**
```bash
nano /home/ubuntu/rag/.env
```

다음 추가:
```env
MODEL_BASE_PATH=./model
# 또는 절대 경로
MODEL_BASE_PATH=/home/ubuntu/rag/backend/model
```

### 해결 4: 메모리 부족 해결

**EC2 인스턴스 타입 확인:**
- 최소 권장: `t3.medium` (2 vCPU, 4GB RAM)
- 모델 크기에 따라 더 큰 인스턴스 필요할 수 있음

**스왑 파일 생성 (임시 해결책):**
```bash
# 4GB 스왑 파일 생성
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구적으로 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## ✅ 확인 체크리스트

- [ ] EC2에 모델 파일 존재 확인 (`backend/model/midm/`)
- [ ] 모델 파일 권한 확인
- [ ] EC2 로그에서 구체적인 오류 확인
- [ ] 메모리 사용량 확인
- [ ] `MODEL_BASE_PATH` 환경 변수 확인
- [ ] 서비스 재시작 후 테스트

## 🧪 테스트 방법

### 1. 모델 파일 존재 확인

```bash
# EC2에서
cd /home/ubuntu/rag
find . -name "config.json" -path "*/model/midm/*"
```

### 2. 모델 로딩 직접 테스트

```bash
# EC2에서 Python으로 테스트
cd /home/ubuntu/rag
source venv/bin/activate
python3 -c "
from backend.llm.loader import get_loader
loader = get_loader()
try:
    llm = loader.load_model('midm', 'midm')
    print('모델 로드 성공!')
except Exception as e:
    print(f'모델 로드 실패: {e}')
"
```

### 3. API 직접 테스트

```bash
# EC2에서
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"테스트","mode":"local"}'
```

## 🆘 여전히 문제가 있으면

1. **EC2 로그 전체 확인:**
   ```bash
   sudo journalctl -u rag-api.service -n 1000 --no-pager > /tmp/rag-api.log
   cat /tmp/rag-api.log
   ```

2. **모델 파일 크기 확인:**
   ```bash
   du -sh /home/ubuntu/rag/backend/model/*
   ```

3. **메모리 및 디스크 확인:**
   ```bash
   free -h
   df -h
   ```

## 💡 임시 해결책

로컬 모델이 EC2에 없거나 메모리가 부족한 경우:

1. **로컬 모델 모드 비활성화** (프론트엔드에서 버튼 숨기기)
2. **OpenAI 모드만 사용**
3. **더 큰 EC2 인스턴스로 업그레이드**
