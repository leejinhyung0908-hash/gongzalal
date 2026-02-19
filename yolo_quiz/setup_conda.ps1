# ============================================================================
# YOLO Quiz Service - Conda 환경 설정 스크립트
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " YOLO Quiz - Conda Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Conda 확인
Write-Host "`n[1/4] Conda 버전 확인..." -ForegroundColor Yellow
conda --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Conda가 설치되어 있지 않습니다." -ForegroundColor Red
    Write-Host "   https://docs.conda.io/en/latest/miniconda.html" -ForegroundColor Gray
    exit 1
}

# 2. 기존 환경 확인
Write-Host "`n[2/4] 기존 환경 확인..." -ForegroundColor Yellow
$envExists = conda env list | Select-String "yolo-quiz"
if ($envExists) {
    Write-Host "기존 yolo-quiz 환경 발견. 삭제 후 재생성합니다..." -ForegroundColor Gray
    conda env remove -n yolo-quiz -y
}

# 3. 환경 생성
Write-Host "`n[3/4] Conda 환경 생성 중 (시간이 걸릴 수 있습니다)..." -ForegroundColor Yellow
conda env create -f environment.yml

# 4. 완료
Write-Host "`n========================================" -ForegroundColor Green
Write-Host " ✅ 설치 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`n환경 활성화:" -ForegroundColor Cyan
Write-Host "  conda activate yolo-quiz" -ForegroundColor White

Write-Host "`nCUDA 확인:" -ForegroundColor Cyan
Write-Host "  python -c `"import torch; print(torch.cuda.is_available())`"" -ForegroundColor White

Write-Host "`n다음 단계:" -ForegroundColor Cyan
Write-Host "  1. conda activate yolo-quiz" -ForegroundColor White
Write-Host "  2. copy config_example.env .env" -ForegroundColor White
Write-Host "  3. python step1_pdf_to_images.py --all" -ForegroundColor White


