# EC2 모델 파일 누락 해결 가이드

## 🔍 문제 확인

EC2에서 모델 디렉토리를 확인한 결과:

**있는 파일:**
- ✅ `config.json` - 모델 설정
- ✅ `tokenizer.json` - 토크나이저
- ✅ `tokenizer_config.json` - 토크나이저 설정
- ✅ 기타 설정 파일들

**없는 파일:**
- ❌ `pytorch_model.bin` - PyTorch 모델 가중치
- ❌ `model.safetensors` - SafeTensors 형식 모델
- ❌ `model.bin` - 일반 모델 가중치

**결론:** 실제 모델 가중치 파일이 없어서 로컬 LLM 모드가 작동하지 않습니다.

## 🔧 해결 방법

### 방법 1: 로컬에서 모델 파일 확인 및 업로드

**1단계: 로컬에서 모델 파일 확인**

로컬 컴퓨터에서:
```bash
# Windows PowerShell
cd C:\Users\hi\Desktop\test3\rag
ls backend/model/midm/
```

**확인할 파일:**
- `pytorch_model.bin` 또는
- `model.safetensors` 또는
- `model.bin`

**2단계: 모델 파일을 EC2에 업로드**

로컬 컴퓨터에서 (Windows PowerShell):
```powershell
# 모델 파일만 업로드 (파일이 큰 경우)
scp -i "kroaddy.pem" backend/model/midm/pytorch_model.bin ubuntu@ec2-13-125-210-86.ap-northeast-2.compute.amazonaws.com:/home/ubuntu/rag/backend/model/midm/

# 또는 전체 모델 디렉토리 재업로드
scp -i "kroaddy.pem" -r backend/model/midm/* ubuntu@ec2-13-125-210-86.ap-northeast-2.compute.amazonaws.com:/home/ubuntu/rag/backend/model/midm/
```

**3단계: EC2에서 확인**

EC2 SSH 접속 후:
```bash
cd /home/ubuntu/rag
ls -lh backend/model/midm/ | grep -E "pytorch|model|safetensors"
```

### 방법 2: Hugging Face에서 직접 다운로드

EC2에서 직접 모델을 다운로드할 수도 있습니다:

```bash
# EC2에서
cd /home/ubuntu/rag
source venv/bin/activate

# Python으로 모델 다운로드
python3 -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
import os

model_name = 'your-model-name'  # 실제 모델 이름으로 변경
model_path = 'backend/model/midm'

print(f'모델 다운로드 시작: {model_name}')
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

print(f'모델 저장 중: {model_path}')
model.save_pretrained(model_path)
tokenizer.save_pretrained(model_path)
print('다운로드 완료!')
"
```

## 📊 모델 파일 크기 확인

**로컬에서 모델 파일 크기 확인:**
```powershell
# Windows PowerShell
Get-ChildItem backend/model/midm/ -Recurse | Where-Object {$_.Name -like "*model*" -or $_.Name -like "*pytorch*"} | Select-Object Name, @{Name="Size(MB)";Expression={[math]::Round($_.Length/1MB,2)}}
```

**EC2 디스크 공간 확인:**
```bash
# EC2에서
df -h
```

모델 파일은 보통 수 GB 크기이므로, EC2에 충분한 디스크 공간이 있는지 확인하세요.

## ✅ 확인 체크리스트

- [ ] 로컬에서 모델 가중치 파일 존재 확인
- [ ] 모델 파일 크기 확인 (디스크 공간 확인)
- [ ] 모델 파일을 EC2에 업로드
- [ ] EC2에서 모델 파일 존재 확인
- [ ] 서비스 재시작
- [ ] 로컬 LLM 모드 테스트

## 🧪 업로드 후 테스트

**1. EC2에서 모델 파일 확인:**
```bash
ls -lh /home/ubuntu/rag/backend/model/midm/ | grep -E "pytorch|model|safetensors|bin"
```

**2. 서비스 재시작:**
```bash
sudo systemctl restart rag-api.service
sudo systemctl status rag-api.service
```

**3. 로그 확인:**
```bash
sudo journalctl -u rag-api.service -n 100 --no-pager | grep -i "model\|load"
```

**4. API 테스트:**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"테스트","mode":"local"}'
```

## 🆘 대안: 로컬 모델 모드 비활성화

모델 파일이 너무 크거나 업로드가 어려운 경우:

**프론트엔드에서 로컬 모델 버튼 숨기기:**
- `frontend/app/page.tsx`에서 로컬 모델 관련 버튼 제거
- 또는 버튼을 비활성화하고 "로컬 모델을 사용할 수 없습니다" 메시지 표시

**백엔드에서 에러 처리 개선:**
- 모델 파일이 없을 때 더 명확한 에러 메시지 반환

## 💡 참고사항

- 모델 파일은 보통 **수 GB ~ 수십 GB** 크기입니다
- EC2 인스턴스 타입에 따라 디스크 공간이 제한될 수 있습니다
- 업로드 시간이 오래 걸릴 수 있습니다 (네트워크 속도에 따라)
- CPU 전용 EC2에서 대형 모델 로드는 메모리 부족을 일으킬 수 있습니다
