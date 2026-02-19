# 초고속 학습용 스크립트 (최대 속도 최적화)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "EXAONE 초고속 학습 (최대 속도 최적화)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "최적화 설정:" -ForegroundColor Yellow
Write-Host "  - 데이터: 1000개 샘플링 (4910개 중)" -ForegroundColor Yellow
Write-Host "  - max-length: 384 (속도 3배 향상)" -ForegroundColor Yellow
Write-Host "  - epochs: 1" -ForegroundColor Yellow
Write-Host "  - LoRA rank: 8 (16 → 8, 속도 향상)" -ForegroundColor Yellow
Write-Host "  - 예상 시간: 약 2-4시간" -ForegroundColor Green
Write-Host ""

python train_exaone_success_stories.py `
    --data data/success_stories/merged_training_data.jsonl `
    --output artifacts/lora-adapters/exaone-success-stories `
    --epochs 1 `
    --batch-size 1 `
    --learning-rate 2e-4 `
    --lora-r 8 `
    --lora-alpha 16 `
    --max-length 384 `
    --gradient-accumulation-steps 8 `
    --max-samples 1000 `
    --use-4bit

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "학습 완료!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

