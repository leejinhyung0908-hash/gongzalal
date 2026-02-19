# 빠른 학습용 스크립트 (속도 최적화)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "EXAONE 빠른 학습 (속도 최적화)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 최적화 설정:
# - max-length: 512 (1024 → 512, 속도 2배 향상)
# - epochs: 1 (빠른 테스트용, 필요시 2로 변경)
# - 동적 패딩 사용

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
    --use-4bit

Write-Host "==========================================" -ForegroundColor Green
Write-Host "학습 완료!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

