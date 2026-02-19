@echo off
REM 빠른 학습용 스크립트 (속도 최적화)

echo ==========================================
echo EXAONE 빠른 학습 (속도 최적화)
echo ==========================================
echo.
echo 최적화 설정:
echo - max-length: 512 (속도 2배 향상)
echo - epochs: 1 (빠른 테스트용)
echo - 동적 패딩 사용
echo.

python train_exaone_success_stories.py ^
    --data data/success_stories/merged_training_data.jsonl ^
    --output artifacts/lora-adapters/exaone-success-stories ^
    --epochs 1 ^
    --batch-size 1 ^
    --learning-rate 2e-4 ^
    --lora-r 16 ^
    --lora-alpha 32 ^
    --max-length 512 ^
    --gradient-accumulation-steps 8 ^
    --use-4bit

echo ==========================================
echo 학습 완료!
echo ==========================================
pause

