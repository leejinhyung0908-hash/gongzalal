# 📝 YOLO 기출 문항 인식 서비스

YOLO를 활용하여 기출 시험지에서 문항을 자동 인식하고, 랜덤 문제 풀이 및 타이머 서비스를 제공합니다.

## 🎯 주요 기능

- **PDF → 이미지 변환**: 기출 시험지를 고해상도 이미지로 변환
- **YOLO 문항 인식**: YOLO11으로 문항 영역 자동 감지
- **자동 크롭**: 개별 문항 이미지로 분리 저장
- **랜덤 문제 풀이**: 과목/연도 필터 + 타이머 기능
- **풀이 기록**: 정답률, 소요 시간, 오답 노트

## 💻 시스템 요구사항

- **OS**: Windows 10/11
- **GPU**: NVIDIA RTX 3050 이상 (CUDA 11.8)
- **RAM**: 16GB 이상 권장
- **Storage**: SSD 256GB (WebP 포맷으로 용량 최적화)
- **Python**: 3.10+

## 🚀 빠른 시작

### 1단계: 가상환경 설정

```powershell
# PowerShell에서 실행
cd yolo_quiz

# 가상환경 생성 및 설정 (스크립트 사용)
.\setup_env.ps1

# 또는 수동 설치
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install ultralytics PyMuPDF Pillow psycopg[binary] sqlalchemy fastapi uvicorn python-multipart numpy opencv-python python-dotenv tqdm pydantic
```

### 2단계: CUDA 확인

```powershell
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

### 3단계: 환경 변수 설정

```powershell
# config_example.env를 .env로 복사
copy config_example.env .env

# .env 파일에 NeonDB 연결 정보 입력
# DATABASE_URL=postgresql://username:password@ep-xxx.neon.tech/dbname?sslmode=require
```

## 📋 단계별 실행

### Step 1: PDF → 이미지 변환

```powershell
# data/pdfs 폴더에 PDF 파일 넣기
# 단일 PDF 변환
python step1_pdf_to_images.py --pdf ./시험지.pdf

# 전체 PDF 변환
python step1_pdf_to_images.py --all
```

### Step 2: YOLO 데이터셋 라벨링

```powershell
# LabelImg 설치 및 실행
pip install labelImg
labelImg

# LabelImg에서:
# 1. Open Dir → data/images 선택
# 2. Change Save Dir → data/labels 선택
# 3. View → YOLO 포맷 선택
# 4. 문항 영역을 드래그하여 라벨링
# 5. Ctrl+S로 저장

# 데이터셋 구성
python step2_prepare_dataset.py --classes question question_number options figure
```

### Step 3: YOLO 모델 학습

```powershell
# 학습 시작 (RTX 3050 기준 배치 8 권장)
python step3_train_yolo.py --epochs 100 --batch 8

# 학습 재개
python step3_train_yolo.py --resume

# 모델 검증
python step3_train_yolo.py --validate
```

### Step 4: 문항 크롭

```powershell
# 학습된 모델로 문항 추출
python step4_crop_questions.py --all --year 2024 --subject 한국사

# 단일 이미지 테스트
python step4_crop_questions.py --image ./data/images/2024_국가직/page_001.png
```

### Step 5: DB 저장

```powershell
# 크롭 결과를 NeonDB에 저장
python step5_save_to_db.py

# 미리보기
python step5_save_to_db.py --dry-run
```

### Step 6: API 서버 실행

```powershell
# 서버 시작
python step6_api_server.py

# 또는 개발 모드
uvicorn step6_api_server:app --reload --port 8000
```

### Step 7: 프론트엔드 실행

```powershell
# 브라우저에서 열기
start step7_frontend.html
```

## 📁 프로젝트 구조

```
yolo_quiz/
├── data/
│   ├── pdfs/           # 원본 PDF 파일
│   ├── images/         # 변환된 이미지
│   ├── labels/         # YOLO 라벨 (txt)
│   ├── crops/          # 크롭된 문항 이미지
│   └── yolo_dataset/   # YOLO 학습 데이터셋
├── models/
│   ├── yolo_questions.pt  # 학습된 모델
│   └── runs/           # 학습 로그
├── config.py           # 설정
├── step1_pdf_to_images.py
├── step2_prepare_dataset.py
├── step3_train_yolo.py
├── step4_crop_questions.py
├── step5_save_to_db.py
├── step6_api_server.py
├── step7_frontend.html
└── requirements.txt
```

## 🗄️ DB 스키마

```
┌─────────────┐       ┌─────────────┐       ┌──────────────────┐
│   exams     │       │  questions  │       │ question_images  │
├─────────────┤       ├─────────────┤       ├──────────────────┤
│ id          │──┐    │ id          │──┐    │ id               │
│ year        │  └───>│ exam_id     │  └───>│ question_id      │
│ subject     │       │ question_no │       │ file_path        │
│ exam_type   │       │ answer_key  │       │ coordinates_json │
└─────────────┘       └─────────────┘       └──────────────────┘
                             │
                             v
                    ┌──────────────────┐
                    │ user_solving_logs│
                    ├──────────────────┤
                    │ user_id          │
                    │ question_id      │
                    │ selected_answer  │
                    │ time_spent       │
                    │ is_wrong_note    │
                    └──────────────────┘
```

## 🎨 API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/questions/random` | 랜덤 문제 조회 |
| POST | `/api/questions/{id}/submit` | 답안 제출 |
| GET | `/api/users/{id}/stats` | 사용자 통계 |
| GET | `/api/subjects` | 과목 목록 |
| GET | `/api/years` | 연도 목록 |

## 🔧 RTX 3050 최적화 팁

1. **VRAM 관리**
   - YOLO 추론: ~2GB
   - 학습: ~4-6GB (batch 8 기준)
   - 큰 배치 사용 시 OOM 발생 가능 → batch 4-8 권장

2. **이미지 용량**
   - WebP 포맷 사용 (PNG 대비 30% 감소)
   - 300 DPI로 충분 (600 DPI 불필요)

3. **Pre-processing**
   - YOLO 크롭은 서비스 전 미리 처리
   - 실시간은 DB + 이미지 파일만 사용

## ❓ 문제 해결

### CUDA를 찾을 수 없음
```powershell
# CUDA 11.8 드라이버 확인
nvidia-smi

# PyTorch 재설치
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### DB 연결 실패
```powershell
# .env 파일 DATABASE_URL 확인
# NeonDB 대시보드에서 연결 문자열 복사
```

### 문항 인식률 낮음
- 더 많은 라벨링 데이터 추가 (최소 100장)
- 학습 에포크 증가 (100 → 200)
- 이미지 해상도 확인 (최소 300 DPI)

## 📜 라이선스

MIT License


