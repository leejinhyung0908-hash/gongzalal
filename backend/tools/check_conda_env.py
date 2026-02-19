"""conda torch313 환경에서 필요한 패키지 확인 스크립트"""

import sys

print(f"Python 버전: {sys.version}")
print(f"Python 경로: {sys.executable}\n")

# 필수 패키지 확인
packages = {
    "torch": "PyTorch",
    "sentence_transformers": "Sentence Transformers",
    "psycopg": "psycopg (PostgreSQL)",
    "pgvector": "pgvector",
    "dotenv": "python-dotenv"
}

missing = []
installed = []

for module, name in packages.items():
    try:
        if module == "dotenv":
            import dotenv
        else:
            __import__(module)
        installed.append(name)
        print(f"[OK] {name} 설치됨")
    except ImportError:
        missing.append(name)
        print(f"[X] {name} 미설치")

print("\n" + "="*50)
if missing:
    print(f"미설치 패키지: {', '.join(missing)}")
    print("\n설치 명령어:")
    print("conda activate torch313")
    for pkg in missing:
        if pkg == "psycopg":
            print("  pip install psycopg[binary]")
        elif pkg == "pgvector":
            print("  pip install pgvector")
        elif pkg == "python-dotenv":
            print("  pip install python-dotenv")
        elif pkg == "Sentence Transformers":
            print("  pip install sentence-transformers")
else:
    print("모든 필수 패키지가 설치되어 있습니다!")

# PyTorch 정보
try:
    import torch
    print(f"\nPyTorch 버전: {torch.__version__}")
    print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA 버전: {torch.version.cuda}")
        print(f"GPU 개수: {torch.cuda.device_count()}")
except ImportError:
    print("\nPyTorch가 설치되지 않았습니다.")

