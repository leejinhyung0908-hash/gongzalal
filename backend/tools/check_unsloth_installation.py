"""Unsloth 설치 확인 스크립트"""

print("=" * 60)
print("Unsloth 설치 확인")
print("=" * 60)

# 1. Unsloth 확인
try:
    from unsloth import FastLanguageModel
    print("\n[OK] Unsloth 설치 완료!")
    print("  - Unsloth를 사용할 수 있습니다.")
except ImportError as e:
    print("\n[오류] Unsloth 설치 실패")
    print(f"  - 오류: {e}")
    print("  - 학습이 불가능합니다.")

# 2. Flash Attention 2 확인
try:
    import flash_attn
    print("\n[OK] Flash Attention 2 설치 완료!")
    print("  - Flash Attention 2를 사용할 수 있습니다.")
except ImportError:
    print("\n[정보] Flash Attention 2 미설치")
    print("  - 선택사항입니다. Unsloth만으로도 충분합니다.")

# 3. xformers 확인
try:
    import xformers
    print("\n[OK] xformers 설치 완료!")
except ImportError:
    print("\n[정보] xformers 미설치")
    print("  - 선택사항입니다. Unsloth는 xformers 없이도 작동합니다.")

# 4. 기타 필수 패키지 확인
required_packages = {
    "torch": "PyTorch",
    "transformers": "Transformers",
    "peft": "PEFT",
    "datasets": "Datasets",
    "trl": "TRL",
    "bitsandbytes": "BitsAndBytes",
}

print("\n" + "=" * 60)
print("필수 패키지 확인")
print("=" * 60)

all_ok = True
for package, name in required_packages.items():
    try:
        __import__(package)
        print(f"[OK] {name}")
    except ImportError:
        print(f"[오류] {name} 미설치")
        all_ok = False

print("\n" + "=" * 60)
if all_ok:
    print("결론: Unsloth 학습 준비 완료!")
    print("  - train_exaone_unsloth.ps1 실행 가능")
else:
    print("결론: 일부 패키지가 누락되었습니다.")
    print("  - install_unsloth.bat를 다시 실행하세요.")
print("=" * 60)

