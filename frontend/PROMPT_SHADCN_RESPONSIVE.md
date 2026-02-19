# shadcn/ui 반응형 컴포넌트 구현 프롬프트

당신은 최고 수준의 **shadcn/ui + Tailwind CSS + Next.js App Router** 전문 프론트엔드 개발자입니다.

모바일과 데스크톱(웹) 버전을 **하나의 컴포넌트 파일** 안에서 자동으로 감지해서 적절히 렌더링하는 패턴을 구현해 주세요.

## 핵심 원칙

1. **단일 컴포넌트 원칙**: 별도의 `MobileXXX` / `DesktopXXX` 컴포넌트를 만들지 말고, **하나의 컴포넌트**로 통합
2. **Tailwind 우선**: 가능한 한 Tailwind CSS의 responsive variant (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`)로 해결
3. **SSR 친화적**: Next.js App Router 환경에서 hydration 에러 없이 작동
4. **성능 최적화**: 불필요한 JavaScript 실행 최소화, 클라이언트 훅은 최소한으로 사용

## 기술 스택 요구사항

- **Framework**: Next.js 16+ (App Router)
- **UI Library**: shadcn/ui 컴포넌트
- **Styling**: Tailwind CSS 3.3+
- **Utilities**:
  - `cn()` from `@/lib/utils` (clsx + tailwind-merge)
  - `cva()` from `class-variance-authority` (variant 관리)
- **Language**: TypeScript (strict mode)

## 반응형 Breakpoint 가이드라인

프로젝트의 `tailwind.config.mjs`에 정의된 breakpoint를 사용:

```typescript
// xs: 475px (작은 모바일)
// sm: 640px (모바일)
// md: 768px (태블릿)
// lg: 1024px (데스크톱)
// xl: 1280px (큰 데스크톱)
// 2xl: 1536px (초대형 데스크톱)
```

**기본 전략**:
- 모바일 우선 접근 (Mobile First)
- `md:` 이상 = 데스크톱으로 간주
- `md:` 미만 = 모바일로 간주

## 구현 패턴

### 1. Tailwind CSS만으로 해결 가능한 경우 (권장)

```tsx
// ✅ 좋은 예: Tailwind responsive variant 사용
<div className="
  flex flex-col gap-4        // 모바일: 세로 배치
  md:flex-row md:gap-8       // 데스크톱: 가로 배치
  p-4                        // 모바일: 작은 패딩
  md:p-8                     // 데스크톱: 큰 패딩
">
  <div className="w-full md:w-1/2">...</div>
  <div className="w-full md:w-1/2">...</div>
</div>
```

### 2. 조건부 렌더링이 필요한 경우

```tsx
'use client'

import { useIsMobile } from '@/lib/hooks/useDevice'

export function ResponsiveComponent() {
  const isMobile = useIsMobile()

  return (
    <>
      {/* 모바일: Sheet 사용 */}
      {isMobile && (
        <Sheet>
          <SheetTrigger>메뉴</SheetTrigger>
          <SheetContent>...</SheetContent>
        </Sheet>
      )}

      {/* 데스크톱: NavigationMenu 사용 */}
      {!isMobile && (
        <NavigationMenu>
          <NavigationMenuList>...</NavigationMenuList>
        </NavigationMenu>
      )}
    </>
  )
}
```

### 3. shadcn/ui 컴포넌트 활용

- **모바일 네비게이션**: `Sheet` 또는 `Drawer`
- **데스크톱 네비게이션**: `NavigationMenu`
- **모달**: 데스크톱은 `Dialog`, 모바일은 `Sheet` (하단 슬라이드)
- **테이블**: 데스크톱은 `Table`, 모바일은 `Card` 리스트
- **그리드**: `Card` 컴포넌트 + Tailwind Grid

## 구현 예시 컴포넌트 유형

### 예시 1: 반응형 네비게이션 바

```tsx
// 데스크톱: 가로 메뉴 + 검색바
// 모바일: 햄버거 아이콘 → Sheet 열기
```

### 예시 2: 반응형 상품 상세 헤더

```tsx
// 데스크톱: 큰 이미지 (좌) + 사이드 정보 패널 (우)
// 모바일: 이미지 (상단) + 정보 (하단 스택) + 고정 하단 버튼
```

### 예시 3: 반응형 폼 레이아웃

```tsx
// 데스크톱: 가로 2~3단 레이아웃 (grid-cols-2, grid-cols-3)
// 모바일: 세로 단일 컬럼 (flex-col)
```

### 예시 4: 반응형 대시보드 카드 그리드

```tsx
// 데스크톱: 3~4열 그리드 (grid-cols-3, grid-cols-4)
// 모바일: 1~2열 (grid-cols-1, sm:grid-cols-2) + 스와이프 가능 carousel 옵션
```

### 예시 5: 반응형 모달/다이얼로그

```tsx
// 데스크톱: 중앙 Dialog (Dialog 컴포넌트)
// 모바일: 하단 Drawer 또는 Sheet (Sheet 컴포넌트, side="bottom")
```

## 필수 구현 사항

### 1. TypeScript 타입 정의

```tsx
interface ResponsiveComponentProps {
  // props 타입 명확히 정의
  className?: string
  variant?: 'default' | 'mobile' | 'desktop'
  // ...
}
```

### 2. cva를 활용한 Variant 관리

```tsx
import { cva, type VariantProps } from 'class-variance-authority'

const responsiveVariants = cva(
  'base-classes',
  {
    variants: {
      layout: {
        mobile: 'flex-col gap-4',
        desktop: 'md:flex-row md:gap-8',
      },
    },
    defaultVariants: {
      layout: 'mobile',
    },
  }
)
```

### 3. 접근성 (a11y) 고려

- 적절한 ARIA 레이블
- 키보드 네비게이션 지원
- 포커스 관리
- 스크린 리더 친화적

### 4. Hydration 에러 방지

```tsx
'use client'

import { useEffect, useState } from 'react'

export function ClientOnlyComponent() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return null // 또는 스켈레톤 UI
  }

  // 클라이언트 전용 로직
}
```

### 5. 성능 최적화

- 불필요한 리렌더링 방지 (useMemo, useCallback)
- 이미지 최적화 (next/image)
- 코드 스플리팅 고려

## 코드 작성 규칙

1. **주석**: 한국어로 작성, 모바일/데스크톱 구분 로직 명확히 표시
2. **네이밍**: 직관적이고 설명적인 이름 (예: `ResponsiveHeader`, `SmartDataTable`, `AdaptiveModal`)
3. **구조**:
   - 컴포넌트 상단에 타입 정의
   - 유틸리티 함수는 컴포넌트 외부에 정의
   - 스타일 관련 상수는 상단에 정의
4. **에러 처리**: 적절한 에러 바운더리 및 폴백 UI

## 체크리스트

구현 후 다음을 확인하세요:

- [ ] 모바일과 데스크톱에서 모두 정상 작동
- [ ] Tailwind responsive variant가 올바르게 적용됨
- [ ] Hydration 에러 없음
- [ ] TypeScript 타입 에러 없음
- [ ] 접근성 기준 충족 (키보드 네비게이션, ARIA 등)
- [ ] 다크 모드 지원
- [ ] 성능 최적화 (불필요한 리렌더링 없음)
- [ ] 주석이 명확하고 이해하기 쉬움

## 추가 고려사항

- **다크 모드**: `dark:` variant 활용
- **애니메이션**: Tailwind transition 클래스 사용
- **테스트**: 가능하면 Storybook이나 테스트 코드 작성
- **문서화**: 컴포넌트 사용법을 JSDoc으로 작성

---

**이 프롬프트를 사용하여 반응형 컴포넌트를 구현해주세요.**

