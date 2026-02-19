# 병렬 구조 분석

## 현재 구조 분석

### ❌ 순차식 구조 (현재)

현재 구조는 **순차식(Sequential)**입니다.

```
Gateway 노드
  ↓
Branch Router 노드
  ↓
하나의 브랜치 노드만 선택 (target_branch)
  ↓
EXAONE 허브
```

**문제점**:
1. `route_after_branch_router()` 함수가 **하나의 브랜치만** 선택
2. `additional_branches`는 PolicyBasedRouter에서 반환하지만 **사용되지 않음**
3. 여러 브랜치가 필요한 경우에도 **하나씩만** 실행

### 현재 코드 분석

#### `route_after_branch_router()` 함수
```python
def route_after_branch_router(state: StarMcpState) -> str:
    """하나의 브랜치만 선택"""
    target_branch = state.get("target_branch")
    # 하나의 브랜치만 반환
    return branch_map.get(target_branch, "spam_filter")
```

#### 그래프 구조
```python
graph.add_conditional_edges(
    "branch_router",
    route_after_branch_router,
    {
        "spam_filter": "spam_filter",      # 하나만 선택
        "sentiment": "sentiment",           # 하나만 선택
        "summary": "summary",              # 하나만 선택
        ...
    }
)
```

## 병렬 구조로 개선

### ✅ 병렬식 구조 (개선안)

여러 브랜치를 **동시에** 실행할 수 있도록 개선:

```
Gateway 노드
  ↓
Branch Router 노드
  ↓
여러 브랜치 노드 동시 실행 (병렬)
  ├─ spam_filter ─┐
  ├─ sentiment ───┤
  └─ summary ─────┘
      ↓
  EXAONE 허브 (모든 결과 수집)
```

### 개선 방법

1. **PolicyBasedRouter에서 여러 브랜치 반환**
2. **Branch Router 노드에서 여러 브랜치 선택**
3. **LangGraph에서 병렬 실행** (여러 노드를 동시에 실행)

---

## 현재 상태 요약

| 항목 | 현재 상태 |
|------|----------|
| **구조** | 순차식 (Sequential) |
| **브랜치 실행** | 하나씩만 실행 |
| **병렬 처리** | ❌ 없음 |
| **additional_branches** | 반환되지만 사용 안 됨 |

---

## 병렬 구조로 개선이 필요한가요?

현재는 순차식이지만, 병렬 구조로 개선할 수 있습니다. 개선하시겠습니까?

