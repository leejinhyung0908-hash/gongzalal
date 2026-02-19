# Unsloth를 사용한 초고속 학습 스크립트

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "EXAONE 초고속 학습 (Unsloth 사용)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Unsloth는 학습 속도를 2-5배 향상시켜줍니다!" -ForegroundColor Green
Write-Host ""
Write-Host "최적화 설정:" -ForegroundColor Yellow
Write-Host "  - 데이터: 1000개 샘플링" -ForegroundColor Yellow
Write-Host "  - max-length: 384" -ForegroundColor Yellow
Write-Host "  - epochs: 1" -ForegroundColor Yellow
Write-Host "  - batch-size: 2 (Unsloth는 더 큰 배치 가능)" -ForegroundColor Yellow
Write-Host "  - Unsloth: 활성화 (2-5배 속도 향상)" -ForegroundColor Yellow
Write-Host "  - Flash Attention 2: 자동 감지 (설치 시 추가 속도 향상)" -ForegroundColor Yellow
Write-Host "  - 예상 시간: 약 1-2시간 (기존 대비 2-5배 빠름!)" -ForegroundColor Green
Write-Host ""

python train_exaone_unsloth.py `
    --data data/success_stories/merged_training_data.jsonl `
    --output artifacts/lora-adapters/exaone-success-stories `
    --epochs 1 `
    --max-samples 1000 `
    --max-length 384 `
    --batch-size 2 `
    --learning-rate 2e-4

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "학습 완료!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

