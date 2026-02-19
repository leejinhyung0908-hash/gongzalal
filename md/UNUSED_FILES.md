# 사용되지 않는 파일/폴더 목록

## 🗑️ 완전히 사용되지 않는 파일

### 1. `backend/services/verdict_agent/graph.py`
- **이유**: 새로운 스타형 구조에서 `backend/services/star_hub/exaone_hub.py`가 EXAONE을 직접 사용하므로 불필요
- **대체**: `backend/services/star_hub/exaone_hub.py`가 EXAONE 허브 역할 수행
- **상태**: 삭제 가능

### 2. `backend/services/verdict_agent/vector_model.py`
- **이유**: 비어있는 파일
- **상태**: 삭제 가능

### 3. `backend/services/text_classifier/check_callcenter.py`
- **이유**: 디버그/검증용 스크립트 (서버 실행에는 불필요)
- **상태**: 삭제 가능 (필요시 재생성 가능)

## ⚠️ 서버 실행에는 불필요하지만 학습에는 필요한 파일들

### `backend/services/spam_agent/` 내 학습 스크립트들
- `lora_adapter.py` - LoRA 학습 스크립트
- `prompt_formatting.py` - 프롬프트 포맷팅
- `data_quality_validation.py` - 데이터 검증
- `run_etl_pipeline.py` - ETL 파이프라인
- `convert_mixed_email_to_exaone.py` - 데이터 변환
- `test_lora_model.py` - 모델 테스트
- 기타 학습 관련 스크립트들

**권장사항**: 학습 스크립트들은 별도 디렉토리(`scripts/` 또는 `training/`)로 이동 고려

### `backend/services/text_classifier/` 내 학습 스크립트들
- `train.py` - koELECTRA 학습 스크립트
- `lora_adapter.py` - LoRA 학습 스크립트

## ✅ 여전히 사용 중인 파일들

### `backend/services/verdict_agent/`
- `base_model.py` ✅ - `GatewayRequest`, `GatewayResponse` 모델 (mcp_controller에서 사용)
- `state_model.py` ✅ - `RequestHistoryState`, `SessionStateState` 모델 (mcp_controller에서 사용)
- `__init__.py` ✅ - 모듈 초기화

### `backend/graph.py`
- ✅ `main.py`에서 `get_local_llm` 사용
- ✅ `routers/chat.py`에서 `run_once` 사용

### `backend/services/mcp_gateway/graph_v2.py`
- ✅ `mcp_tool_koelectra_filter` 함수가 `gateway_strategy.py`에서 사용

## 📋 정리 권장사항

1. **즉시 삭제 가능**:
   - `backend/services/verdict_agent/graph.py`
   - `backend/services/verdict_agent/vector_model.py`
   - `backend/services/text_classifier/check_callcenter.py`

2. **구조 개선 고려**:
   - 학습 스크립트들을 `backend/scripts/` 또는 `backend/training/`으로 이동
   - 서버 실행 코드와 학습 코드 분리

