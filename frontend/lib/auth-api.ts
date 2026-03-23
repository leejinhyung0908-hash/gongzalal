/**
 * 소셜 로그인 API 클라이언트.
 *
 * kroaddy 프로젝트의 lib/api.ts 를 공잘알 프로젝트에 맞게 변환.
 * - NEXT_PUBLIC_API_URL → FastAPI 백엔드(8000 포트) 기준
 * - axios 대신 fetch API 사용 (의존성 최소화)
 *
 * 토큰 전략:
 *   - Access Token  → Upstash Redis (30분 TTL), HTTP-only 쿠키
 *   - Refresh Token → Neon DB (7일 TTL), HTTP-only 쿠키
 *   - 401 수신 시 자동으로 /api/auth/refresh 호출 → 새 Access Token 발급
 */

/** 백엔드 API 기본 URL */
export const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUPLIC_API_URL ||
    "http://localhost:8000";

/** 프로덕션 도메인에서 localhost API를 쓰는 경우(빌드 시 env 누락) */
export function isApiUrlLikelyMisconfiguredForProduction(): boolean {
    if (typeof window === "undefined") return false;
    const host = window.location.hostname;
    const pageIsLocal = host === "localhost" || host === "127.0.0.1";
    if (pageIsLocal) return false;
    return (
        API_BASE_URL.includes("localhost") ||
        API_BASE_URL.includes("127.0.0.1")
    );
}

if (typeof window !== "undefined" && isApiUrlLikelyMisconfiguredForProduction()) {
    console.error(
        "[Auth] NEXT_PUBLIC_API_URL이 프로덕션 빌드에 포함되지 않은 것 같습니다 (현재 API_BASE_URL=%s). " +
            "Vercel → Project → Settings → Environment Variables에 " +
            "NEXT_PUBLIC_API_URL=https://api.leejinhyung.shop 를 추가한 뒤 재배포하세요. " +
            "(NEXT_PUBLIC_* 는 빌드 시점에 고정됩니다.)",
        API_BASE_URL,
    );
}

/** refresh 진행 중 중복 요청 방지 플래그 */
let isRefreshing = false;
/** refresh 완료를 기다리는 대기열 */
let refreshSubscribers: Array<(success: boolean) => void> = [];

/**
 * refresh 완료 후 대기열 처리
 */
function onRefreshComplete(success: boolean) {
    refreshSubscribers.forEach((cb) => cb(success));
    refreshSubscribers = [];
}

/**
 * Access Token 만료 시 Refresh Token으로 자동 갱신
 * @returns 갱신 성공 여부
 */
export const refreshAccessToken = async (): Promise<boolean> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
            method: "POST",
            credentials: "include", // RefreshToken 쿠키 포함
        });

        if (response.ok) {
            console.log("[Auth] Access Token 자동 갱신 성공");
            return true;
        }

        console.warn("[Auth] Access Token 갱신 실패:", response.status);
        return false;
    } catch (error) {
        console.error("[Auth] Access Token 갱신 오류:", error);
        return false;
    }
};

/**
 * 인증이 필요한 API 요청을 보내는 fetch 래퍼.
 * 401 응답 시 자동으로 refresh를 시도하고 원래 요청을 재시도합니다.
 */
export const authFetch = async (
    url: string,
    options: RequestInit = {}
): Promise<Response> => {
    // 쿠키 포함 설정
    const fetchOptions: RequestInit = {
        ...options,
        credentials: "include",
    };

    let response = await fetch(url, fetchOptions);

    // 401 (Unauthorized) → refresh 시도
    if (response.status === 401) {
        if (!isRefreshing) {
            isRefreshing = true;

            const refreshSuccess = await refreshAccessToken();
            isRefreshing = false;
            onRefreshComplete(refreshSuccess);

            if (refreshSuccess) {
                // 원래 요청 재시도
                response = await fetch(url, fetchOptions);
            } else {
                // Refresh 실패 → 게스트/비로그인 계속 (자동 /login 이동 없음)
                console.warn("[Auth] Refresh 실패 - 비로그인으로 계속");
            }
        } else {
            // 이미 refresh 진행 중 → 완료될 때까지 대기
            const success = await new Promise<boolean>((resolve) => {
                refreshSubscribers.push(resolve);
            });

            if (success) {
                response = await fetch(url, fetchOptions);
            }
        }
    }

    return response;
};

/**
 * 소셜 로그인 인가 URL 가져오기
 * @param provider - 'kakao' | 'naver' | 'google'
 * @returns 인가 URL 문자열
 */
export const getSocialLoginUrl = async (provider: string): Promise<string> => {
    // 로그아웃 후 재인증 플래그 확인 (삭제하지 않음 — 로그인 성공 시에만 제거)
    const forceReauth = isForceReauth();
    const url = `${API_BASE_URL}/api/auth/${provider}/login${forceReauth ? "?force_reauth=true" : ""}`;

    console.log(`[Auth] ${provider} 로그인 URL 요청: ${url} (force_reauth=${forceReauth})`);

    const response = await fetch(url, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
        const errText = await response.text().catch(() => "");
        const isNetworkError = !response.status;

        if (isNetworkError || response.status >= 500) {
            throw new Error(
                `백엔드 서버에 연결할 수 없습니다.\n` +
                `확인 사항:\n` +
                `1. 백엔드 서버 실행 확인: ${API_BASE_URL}\n` +
                `2. CORS 설정 확인\n` +
                `3. 환경 변수 설정 확인`
            );
        }
        throw new Error(`HTTP ${response.status}: ${errText}`);
    }

    const data = await response.json();

    if (!data.authUrl) {
        throw new Error(`응답에 authUrl이 없습니다.`);
    }

    console.log(`[Auth] ${provider} 인가 URL 수신 완료`);
    return data.authUrl;
};

/**
 * 소셜 로그인 시작 (인가 URL 로 리다이렉트)
 * @param provider - 'kakao' | 'naver' | 'google'
 *
 * 네이버의 경우: prompt=login 을 지원하지 않으므로,
 * 로그아웃 후 재인증 시 팝업으로 네이버 세션을 먼저 해제합니다.
 * 팝업은 사용자 클릭 직후 동기적으로 열어야 브라우저 팝업 차단기를 피합니다.
 */
export const startSocialLogin = async (provider: string): Promise<void> => {
    try {
        // ── 네이버: force_reauth 시 세션 해제용 팝업을 *동기적으로* 먼저 열기 ──
        // window.open 은 사용자 클릭(동기 호출 스택) 안에서 실행해야 팝업 차단 안됨
        let naverLogoutPopup: Window | null = null;
        if (provider === "naver" && isForceReauth()) {
            console.log("[Auth] 네이버 세션 해제 팝업 열기...");
            naverLogoutPopup = window.open(
                "https://nid.naver.com/nidlogin.logout",
                "naver_logout",
                "width=100,height=100,left=-9999,top=-9999"
            );
        }

        // ── 백엔드에서 인가 URL 가져오기 (async) ──
        const authUrl = await getSocialLoginUrl(provider);
        console.log(`[Auth] ${provider} 로그인 페이지로 리다이렉트...`);

        // ── 네이버: 팝업에서 세션 해제가 완료될 때까지 2초 대기 ──
        if (naverLogoutPopup) {
            console.log("[Auth] 네이버 세션 해제 대기 중 (2초)...");
            await new Promise((resolve) => setTimeout(resolve, 2000));
            try { naverLogoutPopup.close(); } catch { /* 이미 닫혔을 수 있음 */ }
            console.log("[Auth] 네이버 세션 해제 완료, 인증 페이지로 이동");
        }

        window.location.href = authUrl;
    } catch (error) {
        const msg = error instanceof Error ? error.message : String(error);
        console.error(`[Auth] 소셜 로그인 시작 실패 (${provider}):`, msg);
        const vercelHint = isApiUrlLikelyMisconfiguredForProduction()
            ? "\n\n[Vercel] NEXT_PUBLIC_API_URL=https://api.leejinhyung.shop 를 Production에 넣고 **재배포**해야 합니다. (로컬 .env만으로는 배포물에 반영되지 않습니다.)"
            : "";
        alert(
            `로그인에 실패했습니다.\n\n${msg}\n\n` +
                `확인 사항:\n` +
                `1. 백엔드 서버 실행 확인 (${API_BASE_URL})\n` +
                `2. Vercel 환경 변수 NEXT_PUBLIC_API_URL 설정 후 재배포\n` +
                `3. 백엔드 CORS에 https://leejinhyung.shop 포함 여부` +
                vercelHint,
        );
    }
};

/**
 * 현재 로그인된 사용자 정보 조회 (쿠키 기반).
 * Access Token 만료 시 자동으로 refresh를 시도합니다.
 * @returns 사용자 정보 또는 null
 *   - id: DB 정수 user_id (FK 참조용)
 *   - social_id: 소셜 로그인 원본 ID
 *   - display_name: 닉네임
 *   - provider: 'kakao' | 'naver' | 'google'
 *   - linked_accounts: 연동된 소셜 계정 목록
 */
export const getCurrentUser = async (): Promise<{
    id: number | null;
    social_id: string;
    display_name: string | null;
    provider: string | null;
    linked_accounts?: Array<{
        provider: string;
        social_id: string;
        email: string | null;
        linked_at: string | null;
    }>;
} | null> => {
    try {
        const response = await authFetch(`${API_BASE_URL}/api/auth/me`);

        if (!response.ok) return null;

        return await response.json();
    } catch {
        return null;
    }
};

/**
 * 소셜 계정 연동 URL 가져오기 (로그인 상태에서 다른 소셜 계정 연동)
 * @param provider - 'kakao' | 'naver' | 'google'
 * @returns 연동용 인가 URL
 */
export const getSocialLinkUrl = async (provider: string): Promise<string> => {
    const url = `${API_BASE_URL}/api/auth/${provider}/link`;

    console.log(`[Auth] ${provider} 계정 연동 URL 요청: ${url}`);

    const response = await authFetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
        const errText = await response.text().catch(() => "");
        throw new Error(`계정 연동 URL 요청 실패 (HTTP ${response.status}): ${errText}`);
    }

    const data = await response.json();

    if (!data.authUrl) {
        throw new Error("응답에 authUrl이 없습니다.");
    }

    console.log(`[Auth] ${provider} 연동 인가 URL 수신 완료`);
    return data.authUrl;
};

/**
 * 소셜 계정 연동 시작 (인가 URL 로 리다이렉트)
 * @param provider - 'kakao' | 'naver' | 'google'
 */
export const startSocialLink = async (provider: string): Promise<void> => {
    try {
        const authUrl = await getSocialLinkUrl(provider);
        console.log(`[Auth] ${provider} 계정 연동 페이지로 리다이렉트...`);
        window.location.href = authUrl;
    } catch (error) {
        const msg = error instanceof Error ? error.message : String(error);
        console.error(`[Auth] 계정 연동 시작 실패 (${provider}):`, msg);
        throw error;
    }
};

// ─── 연동 프로바이더 localStorage 관리 ────────────────────────────
// 로그아웃 후에도 어떤 소셜 계정이 연동되어 있는지 기억하여,
// 미연동 프로바이더 로그인을 차단하는 데 사용합니다.

const LS_KEY_LINKED_PROVIDERS = "gja_linked_providers";

/**
 * 연동된 프로바이더 목록을 localStorage에 저장
 */
export const storeLinkedProviders = (providers: string[]): void => {
    try {
        localStorage.setItem(LS_KEY_LINKED_PROVIDERS, JSON.stringify(providers));
    } catch { /* localStorage 사용 불가 시 무시 */ }
};

/**
 * localStorage에 저장된 연동 프로바이더 목록 조회
 * @returns 프로바이더 배열 또는 null(최초 사용자)
 */
export const getStoredLinkedProviders = (): string[] | null => {
    try {
        const raw = localStorage.getItem(LS_KEY_LINKED_PROVIDERS);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : null;
    } catch {
        return null;
    }
};

/**
 * localStorage의 연동 프로바이더 정보 삭제 (전체 초기화용)
 */
export const clearStoredLinkedProviders = (): void => {
    try {
        localStorage.removeItem(LS_KEY_LINKED_PROVIDERS);
    } catch { /* 무시 */ }
};


// ─── 재인증 플래그 (로그아웃 후 소셜 재인증 강제) ─────────────────
const LS_KEY_FORCE_REAUTH = "gja_force_reauth";

/**
 * 재인증 플래그가 설정되어 있는지 확인 (삭제하지 않음).
 * 로그인 시도마다 확인하여, 새로고침/뒤로가기 후에도 재인증을 유지합니다.
 * 플래그는 로그인 성공 후에만 clearForceReauth()로 삭제합니다.
 */
export const isForceReauth = (): boolean => {
    try {
        return localStorage.getItem(LS_KEY_FORCE_REAUTH) === "true";
    } catch { return false; }
};

/**
 * 재인증 플래그 제거 (로그인 성공 후 호출)
 */
export const clearForceReauth = (): void => {
    try { localStorage.removeItem(LS_KEY_FORCE_REAUTH); } catch { /* 무시 */ }
};


/**
 * 로그아웃: 백엔드 로그아웃 리다이렉트 엔드포인트로 이동.
 *
 * 로그인 시 쿠키가 302 리다이렉트 응답으로 설정되므로,
 * 로그아웃도 동일하게 리다이렉트(풀 페이지 네비게이션)로 처리해야
 * 크로스오리진 환경에서 브라우저가 확실하게 쿠키를 제거합니다.
 *
 * 추가로 재인증 플래그를 설정하여, 다음 소셜 로그인 시
 * 소셜 프로바이더(카카오/네이버/구글)에서도 재로그인을 요구합니다.
 */
export const logout = (): void => {
    try { localStorage.setItem(LS_KEY_FORCE_REAUTH, "true"); } catch { /* 무시 */ }
    window.location.href = `${API_BASE_URL}/api/auth/logout`;
};
