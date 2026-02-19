# 균형잡힌 학습용 스크립트 (속도와 품질의 균형)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "EXAONE 균형 학습 (속도와 품질의 균형)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "최적화 설정:" -ForegroundColor Yellow
Write-Host "  - 데이터: 2000개 샘플링 (4910개 중)" -ForegroundColor Yellow
Write-Host "  - max-length: 512" -ForegroundColor Yellow
Write-Host "  - epochs: 1" -ForegroundColor Yellow
Write-Host "  - LoRA rank: 16" -ForegroundColor Yellow
Write-Host "  - 예상 시간: 약 4-6시간" -ForegroundColor Green
Write-Host ""

python train_exaone_success_stories.py `
    --data data/success_stories/merged_training_data.jsonl `
    --output artifacts/lora-adapters/exaone-success-stories `
    --epochs 1 `
    --batch-size 1 `
    --learning-rate 2e-4 `
    --lora-r 16 `
    --lora-alpha 32 `
    --max-length 512 `
    --gradient-accumulation-steps 8 `
    --max-samples 2000 `
    --use-4bit

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "학습 완료!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

