/**
 * 게스트(일회성) 세션 — sessionStorage / localStorage 키 및 정리 유틸.
 * 로그인 성공 시 clearGuestSessionData()로 전부 제거합니다.
 */

export const GUEST_MODE_KEY = "gja_guest_mode";
export const GUEST_PROFILE_KEY = "gja_guest_profile";
export const GUEST_SOLVING_LOGS_KEY = "gja_guest_solving_logs";

/** 로그인 페이지에서 「게스트로 입장하기」 클릭 시 호출 */
export function markGuestEntry(): void {
    if (typeof window === "undefined") return;
    try {
        sessionStorage.setItem(GUEST_MODE_KEY, "1");
    } catch {
        /* ignore */
    }
}

/** 로그인 성공 시 게스트 임시 데이터 전부 삭제 */
export function clearGuestSessionData(): void {
    if (typeof window === "undefined") return;
    try {
        sessionStorage.removeItem(GUEST_MODE_KEY);
        sessionStorage.removeItem(GUEST_SOLVING_LOGS_KEY);
        localStorage.removeItem(GUEST_PROFILE_KEY);
        // 채팅 임시 이력 (게스트/비로그인 공통 키)
        sessionStorage.removeItem("chat_messages");
        sessionStorage.removeItem("chat_thread_id");
    } catch {
        /* ignore */
    }
}

export function isGuestEntryActive(): boolean {
    if (typeof window === "undefined") return false;
    try {
        return sessionStorage.getItem(GUEST_MODE_KEY) === "1";
    } catch {
        return false;
    }
}
