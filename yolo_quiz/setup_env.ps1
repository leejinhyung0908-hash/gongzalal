# ============================================================================
# YOLO 기출 문항 인식 서비스 - 가상환경 설정 스크립트 (Windows PowerShell)
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " YOLO Quiz Service - Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Python 버전 확인
Write-Host "`n[1/5] Python 버전 확인..." -ForegroundColor Yellow
python --version

# 2. 가상환경 생성
Write-Host "`n[2/5] 가상환경 생성 (.venv)..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "기존 가상환경 발견. 삭제 후 재생성..." -ForegroundColor Gray
    Remove-Item -Recurse -Force ".venv"
}
python -m venv .venv

# 3. 가상환경 활성화
Write-Host "`n[3/5] 가상환경 활성화..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

# 4. pip 업그레이드
Write-Host "`n[4/5] pip 업그레이드..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# 5. PyTorch CUDA 버전 설치 (RTX 3050용)
Write-Host "`n[5/5] PyTorch CUDA 11.8 설치 (RTX 3050 최적화)..." -ForegroundColor Yellow
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 6. 나머지 의존성 설치
Write-Host "`n[6/6] 나머지 패키지 설치..." -ForegroundColor Yellow
pip install ultralytics PyMuPDF Pillow psycopg[binary] sqlalchemy fastapi uvicorn python-multipart numpy opencv-python python-dotenv tqdm pydantic

# 완료
Write-Host "`n========================================" -ForegroundColor Green
Write-Host " 설치 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`n다음 명령어로 CUDA 확인:" -ForegroundColor Cyan
Write-Host "  python -c `"import torch; print(torch.cuda.is_available())`"" -ForegroundColor White

Write-Host "`n가상환경 활성화:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White


