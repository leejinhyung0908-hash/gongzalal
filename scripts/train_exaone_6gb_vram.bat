@echo off
REM 6GB VRAM (RTX 3050) 최적화된 EXAONE 학습 스크립트 (Windows)

echo ==========================================
echo EXAONE 학습 (6GB VRAM 최적화)
echo ==========================================

python train_exaone_success_stories.py ^
    --data data/success_stories/merged_training_data.jsonl ^
    --output artifacts/lora-adapters/exaone-success-stories ^
    --epochs 3 ^
    --batch-size 1 ^
    --learning-rate 2e-4 ^
    --lora-r 16 ^
    --lora-alpha 32 ^
    --max-length 1024 ^
    --gradient-accumulation-steps 8 ^
    --use-4bit

echo ==========================================
echo 학습 완료!
echo ==========================================
pause

