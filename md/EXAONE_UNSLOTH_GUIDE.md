# EXAONE Fine-tuning with Unsloth + Flash Attention 2

Unsloth와 Flash Attention 2를 사용한 초고속 EXAONE 학습 가이드입니다.

## 🚀 설치

### 전체 설치 (권장)

```powershell
.\install_unsloth.bat
```

이 스크립트는 다음을 설치합니다:
- Unsloth (2-5배 속도 향상)
- Flash Attention 2 (추가 속도 및 메모리 최적화)
- 필요한 의존성 패키지

### Flash Attention 2만 설치

```powershell
.\install_flash_attention.bat
```

**주의**: Flash Attention 2는 컴파일이 필요하므로 10-30분이 걸릴 수 있습니다.

## 📊 성능 비교

| 설정 | 배치 크기 | 데이터 | 예상 시간 | 속도 향상 |
|------|----------|--------|----------|----------|
| 기본 방식 | 1 | 1000개 | 2-4시간 | 1x |
| Unsloth만 | 2 | 1000개 | 1-2시간 | 2-3x |
| **Unsloth + Flash Attention 2** | **2-4** | **1000개** | **30분-1시간** | **4-8x** |

## 🎯 학습 실행

### Unsloth + Flash Attention 2 사용

```powershell
.\train_exaone_unsloth.ps1
```

### 수동 실행

```powershell
python train_exaone_unsloth.py `
    --data data/success_stories/merged_training_data.jsonl `
    --output artifacts/lora-adapters/exaone-success-stories `
    --epochs 1 `
    --max-samples 1000 `
    --max-length 384 `
    --batch-size 2 `
    --learning-rate 2e-4
```

## ⚙️ 최적화 옵션

### Flash Attention 2의 장점

1. **메모리 효율**: 더 긴 시퀀스 길이 처리 가능
2. **속도 향상**: Attention 연산 최적화
3. **배치 크기 증가**: 더 큰 배치로 학습 가능

### 권장 설정 (6GB VRAM)

- **Unsloth만**: `--batch-size 2`, `--max-length 384`
- **Unsloth + Flash Attention 2**: `--batch-size 4`, `--max-length 512` (더 긴 시퀀스 가능)

## 🔍 문제 해결

### Flash Attention 2 설치 실패

Flash Attention 2 설치가 실패해도 학습은 가능합니다. Unsloth만으로도 충분한 속도 향상을 얻을 수 있습니다.

### CUDA 버전 확인

Flash Attention 2는 CUDA 11.6 이상이 필요합니다:
```powershell
nvidia-smi
```

### 컴파일 오류

Windows에서 Flash Attention 2 컴파일이 실패할 수 있습니다. 이 경우:
1. Visual Studio Build Tools 설치 확인
2. 또는 Unsloth만 사용 (충분히 빠름)

## 📝 참고사항

- Flash Attention 2는 선택사항입니다. Unsloth만으로도 충분합니다.
- 설치 시간이 오래 걸릴 수 있지만, 한 번만 설치하면 됩니다.
- 학습 중 자동으로 Flash Attention 2를 감지하고 사용합니다.

