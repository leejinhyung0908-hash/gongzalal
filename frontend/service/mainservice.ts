/**
 * 소셜 로그인 핸들러.
 *
 * kroaddy 프로젝트의 service/mainservice.ts 를 공잘알 프로젝트에 맞게 변환.
 */

import { API_BASE_URL, startSocialLogin } from "@/lib/auth-api";

/**
 * 소셜 로그인 핸들러를 생성하는 IIFE
 */
export const { handleKakaoLogin, handleNaverLogin, handleGoogleLogin } = (() => {
    /** Gateway 로그를 기록하는 공통 함수 */
    const logLoginAction = async (action: string): Promise<void> => {
        try {
            await fetch(`${API_BASE_URL}/api/log/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ action }),
            }).catch(() => { });
        } catch {
            // 로그 기록 실패는 무시
        }
    };

    /** 카카오 로그인 핸들러 */
    const handleKakaoLogin = async (): Promise<void> => {
        try {
            await logLoginAction("카카오 로그인 시작");
            await startSocialLogin("kakao");
        } catch (error) {
            console.error("카카오 로그인 실패:", error);
        }
    };

    /** 네이버 로그인 핸들러 */
    const handleNaverLogin = async (): Promise<void> => {
        try {
            await logLoginAction("네이버 로그인 시작");
            await startSocialLogin("naver");
        } catch (error) {
            console.error("네이버 로그인 실패:", error);
        }
    };

    /** 구글 로그인 핸들러 */
    const handleGoogleLogin = async (): Promise<void> => {
        try {
            await logLoginAction("구글 로그인 시작");
            await startSocialLogin("google");
        } catch (error) {
            console.error("구글 로그인 실패:", error);
        }
    };

    return {
        handleKakaoLogin,
        handleNaverLogin,
        handleGoogleLogin,
    };
})();

