@echo off
REM Unsloth + Flash Attention 2 라이브러리 설치 스크립트

echo ==========================================
echo Unsloth + Flash Attention 2 설치
echo ==========================================
echo.
echo Unsloth: 학습 속도를 2-5배 향상
echo Flash Attention 2: 메모리 효율 및 속도 향상
echo.

echo [1/3] Unsloth 설치 중...
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps "xformers<0.0.27" trl peft accelerate bitsandbytes

echo.
echo [2/3] Flash Attention 2 설치 중...
echo (이 단계는 시간이 걸릴 수 있습니다...)
pip install flash-attn --no-build-isolation

echo.
echo [3/3] 추가 패키지 설치 중...
pip install ninja

echo.
echo ==========================================
echo 설치 완료!
echo ==========================================
echo.
echo Flash Attention 2는 컴파일이 필요하므로 시간이 걸릴 수 있습니다.
echo 설치가 실패하면 Flash Attention 없이도 학습 가능합니다.
echo.
pause

