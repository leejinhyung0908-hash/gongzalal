@echo off
REM Flash Attention 2만 설치하는 스크립트

echo ==========================================
echo Flash Attention 2 설치
echo ==========================================
echo.
echo Flash Attention 2는 attention 연산을 최적화하여
echo 메모리 사용량을 줄이고 속도를 향상시킵니다.
echo.
echo 주의: 컴파일이 필요하므로 시간이 걸립니다 (10-30분)
echo.

pip install ninja
pip install flash-attn --no-build-isolation

echo.
echo ==========================================
echo 설치 완료!
echo ==========================================
echo.
echo Flash Attention 2가 설치되었습니다.
echo 이제 학습 시 자동으로 사용됩니다.
echo.
pause

