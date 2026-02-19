"""프로젝트 설정."""

import os
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 기본 경로
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# 데이터 경로
# 기본 PDF 경로를 기출 시험지 폴더로 설정
PDF_INPUT_DIR = Path(os.getenv("PDF_INPUT_DIR", r"C:\Users\hi\Desktop\private\data\gongmuwon\raw\exampaper"))
IMAGE_OUTPUT_DIR = Path(os.getenv("IMAGE_OUTPUT_DIR", DATA_DIR / "images"))
CROP_OUTPUT_DIR = Path(os.getenv("CROP_OUTPUT_DIR", DATA_DIR / "crops"))
LABELS_DIR = DATA_DIR / "labels"

# 디렉토리 생성
for dir_path in [PDF_INPUT_DIR, IMAGE_OUTPUT_DIR, CROP_OUTPUT_DIR, LABELS_DIR, MODELS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# DB 설정
DATABASE_URL = os.getenv("DATABASE_URL", "")

# YOLO 설정
YOLO_MODEL_PATH = Path(os.getenv("YOLO_MODEL_PATH", MODELS_DIR / "yolo_questions.pt"))
YOLO_CONFIDENCE = float(os.getenv("YOLO_CONFIDENCE", "0.5"))

# 이미지 설정
IMAGE_DPI = 300  # PDF 변환 해상도
IMAGE_FORMAT = "webp"  # 저장 포맷 (용량 효율)
IMAGE_QUALITY = 85  # WebP 품질

# 서버 설정
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

