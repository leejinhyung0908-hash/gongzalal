#!/bin/bash
# conda torch313 환경에서 필요한 패키지 설치 스크립트

echo "conda torch313 환경 활성화 중..."
conda activate torch313

echo "필수 패키지 설치 중..."
pip install sentence-transformers

echo "설치 완료!"
echo ""
echo "다음 명령어로 스크립트를 실행하세요:"
echo "  conda activate torch313"
echo "  python create_embeddings_for_neon.py"

