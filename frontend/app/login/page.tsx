"use client";

import { useState, useEffect } from "react";
import { handleKakaoLogin, handleNaverLogin, handleGoogleLogin } from "@/service/mainservice";
import { API_BASE_URL, getStoredLinkedProviders, storeLinkedProviders } from "@/lib/auth-api";

const PARTICLES = [
    { left: "3%", delay: "0s", duration: "9s", opacity: 0.15 },
    { left: "12%", delay: "3s", duration: "11s", opacity: 0.22 },
    { left: "22%", delay: "6s", duration: "8s", opacity: 0.18 },
    { left: "35%", delay: "1.5s", duration: "10s", opacity: 0.28 },
    { left: "45%", delay: "4s", duration: "12s", opacity: 0.2 },
    { left: "55%", delay: "7s", duration: "9.5s", opacity: 0.25 },
    { left: "65%", delay: "2s", duration: "11s", opacity: 0.17 },
    { left: "75%", delay: "5s", duration: "8.5s", opacity: 0.3 },
    { left: "85%", delay: "0.5s", duration: "10s", opacity: 0.2 },
    { left: "95%", delay: "3.5s", duration: "13s", opacity: 0.16 },
];

const ALL_PROVIDERS = ["kakao", "naver", "google"] as const;

export default function LoginPage() {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [linkedProviders, setLinkedProviders] = useState<string[]>([]);
    const [toastMsg, setToastMsg] = useState<string | null>(null);

    // ── 로그인 상태 + 연동 프로바이더 확인 ──
    // 1. /api/auth/me 로 현재 로그인 여부 확인
    //    → 로그인 상태: isLoggedIn=true, linkedProviders 세팅, localStorage 동기화
    // 2. 비로그인(로그아웃 후 복귀)이면 localStorage 에서 연동 정보 복원
    //    → 미연동 프로바이더는 비활성 유지
    // 3. localStorage 에도 없으면 → 최초 사용자 → 전체 활성
    useEffect(() => {
        const checkAuth = async () => {
            try {
                const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
                    credentials: "include",
                });

                if (res.ok) {
                    const user = await res.json();
                    if (user && user.id) {
                        setIsLoggedIn(true);
                        const providers: string[] = [];
                        if (user.linked_accounts) {
                            user.linked_accounts.forEach((acc: { provider?: string }) => {
                                if (acc.provider && !providers.includes(acc.provider)) {
                                    providers.push(acc.provider);
                                }
                            });
                        }
                        if (user.provider && !providers.includes(user.provider)) {
                            providers.push(user.provider);
                        }
                        setLinkedProviders(providers);
                        // localStorage 동기화
                        if (providers.length > 0) storeLinkedProviders(providers);
                        return;
                    }
                }
            } catch {
                // 네트워크 오류 — 아래 fallback 로 진행
            }

            // 비로그인 상태 → localStorage fallback
            const stored = getStoredLinkedProviders();
            if (stored && stored.length > 0) {
                setLinkedProviders(stored);
            }
            // stored가 null이면 최초 사용자 → linkedProviders=[] → 전체 활성
        };
        checkAuth();
    }, []);

    // 토스트 자동 사라짐
    useEffect(() => {
        if (!toastMsg) return;
        const t = setTimeout(() => setToastMsg(null), 3000);
        return () => clearTimeout(t);
    }, [toastMsg]);

    const handleSocialClick = (
        provider: string,
        handler: () => Promise<void>,
    ) => {
        const hasHistory = linkedProviders.length > 0;
        const isLinked = linkedProviders.includes(provider);

        // ── 로그인 상태 ──
        if (isLoggedIn) {
            if (isLinked) {
                // 이미 연동된 프로바이더 → 바로 채팅
                window.location.href = "/chat";
            } else {
                // 미연동 → 안내 메시지
                setToastMsg("사용자 정보 페이지에서 먼저 계정연동을 진행해주세요.");
            }
            return;
        }

        // ── 비로그인 + 기존 사용자(로그아웃 후 복귀) ──
        if (hasHistory) {
            if (isLinked) {
                // 연동된 프로바이더 → 정상 로그인 진행
                handler();
            } else {
                // 미연동 프로바이더 → 차단
                setToastMsg("사용자 정보 페이지에서 먼저 계정연동을 진행해주세요.");
            }
            return;
        }

        // ── 최초 사용자(localStorage 없음) → 모든 소셜 로그인 허용 ──
        handler();
    };

    return (
        <div className="login-container">
            {/* 토스트 메시지 */}
            {toastMsg && (
                <div className="toast-message">
                    <span className="toast-icon">ℹ️</span>
                    <span>{toastMsg}</span>
                </div>
            )}

            {/* 배경 파티클 */}
            <div className="particles">
                {PARTICLES.map((p, i) => (
                    <span
                        key={i}
                        className="particle"
                        style={{
                            left: p.left,
                            animationDelay: p.delay,
                            animationDuration: p.duration,
                            opacity: p.opacity,
                        }}
                    />
                ))}
            </div>

            {/* 로고 */}
            <a href="/" className="logo">
                <span className="logo-char">공</span>
                <span className="logo-char">잘</span>
                <span className="logo-char">알</span>
            </a>

            {/* 로그인 카드 */}
            <div className="login-card">
                <h2 className="login-title">로그인</h2>

                {/* 소셜 로그인 아이콘 */}
                <div className="social-buttons">
                    {(["kakao", "naver", "google"] as const).map((provider) => {
                        const hasHistory = linkedProviders.length > 0;
                        const isLinked = linkedProviders.includes(provider);
                        const isLocked = hasHistory && !isLinked;
                        const handlers = {
                            kakao: handleKakaoLogin,
                            naver: handleNaverLogin,
                            google: handleGoogleLogin,
                        };
                        const labels = { kakao: "카카오", naver: "네이버", google: "구글" };

                        return (
                            <div className="social-btn-wrap" key={provider}>
                                <button
                                    className={`social-btn ${provider} ${isLocked ? "social-btn-locked" : ""} ${isLoggedIn && isLinked ? "social-btn-linked" : ""}`}
                                    onClick={() => handleSocialClick(provider, handlers[provider])}
                                >
                                    <img
                                        src={`/images/login/${provider}.png`}
                                        alt={`${labels[provider]} 로그인`}
                                        className="social-icon"
                                    />
                                </button>
                                {isLoggedIn && isLinked && (
                                    <span className={`linked-dot ${provider}-dot`} />
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* 연동 안내 + 초기화 (비활성 프로바이더가 있을 때) */}
                {linkedProviders.length > 0 && linkedProviders.length < ALL_PROVIDERS.length && (
                    <p className="link-hint">
                        🔗 다른 소셜 계정을 연동하려면{" "}
                        <a href="/user" className="link-hint-anchor">사용자 정보</a> 페이지에서 계정연동을 진행하세요.
                    </p>
                )}

                {/* 구분선 */}
                <div className="divider">
                    <span className="divider-line" />
                    <span className="divider-text">또는</span>
                    <span className="divider-line" />
                </div>

                {/* 게스트 입장 버튼 */}
                <button
                    className="guest-btn"
                    onClick={() => {
                        if (isLoggedIn) {
                            // 로그인 상태: 먼저 로그아웃 후 /chat으로 이동
                            window.location.href = `${API_BASE_URL}/api/auth/logout?next=/chat`;
                        } else {
                            window.location.href = "/chat";
                        }
                    }}
                >
                    <span className="guest-btn-text">게스트로 입장하기</span>
                    <span className="guest-btn-line" />
                </button>

                <div className="login-footer">
                    <a href="/" className="footer-link">메인으로</a>
                </div>
            </div>

            <style jsx>{`
                .login-container {
                    position: relative;
                    width: 100vw;
                    height: 100vh;
                    background: #000;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                    font-family:
                        "Gothic A1",
                        "Noto Sans KR",
                        "Malgun Gothic",
                        "맑은 고딕",
                        sans-serif;
                }

                /* ── 파티클 ── */
                .particles {
                    position: absolute;
                    inset: 0;
                    pointer-events: none;
                }

                .particle {
                    position: absolute;
                    bottom: -20px;
                    width: 2px;
                    height: 2px;
                    background: rgba(255, 255, 255, 0.6);
                    border-radius: 50%;
                    animation: rise linear infinite;
                }

                @keyframes rise {
                    0% {
                        transform: translateY(0) scale(1);
                        opacity: 0;
                    }
                    10% {
                        opacity: 0.4;
                    }
                    90% {
                        opacity: 0.1;
                    }
                    100% {
                        transform: translateY(-100vh) scale(0.3);
                        opacity: 0;
                    }
                }

                /* ── 로고 ── */
                .logo {
                    display: flex;
                    gap: 4px;
                    text-decoration: none;
                    margin-bottom: 48px;
                    animation: fadeIn 1s ease-out both;
                }

                .logo-char {
                    font-size: 2rem;
                    font-weight: 900;
                    color: #fff;
                    text-shadow: 0 0 20px rgba(255, 255, 255, 0.1);
                    user-select: none;
                }

                /* ── 카드 ── */
                .login-card {
                    position: relative;
                    width: min(380px, 85vw);
                    padding: 40px 36px;
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 16px;
                    backdrop-filter: blur(12px);
                    animation: fadeInUp 1s ease-out 0.2s both;
                }

                .login-title {
                    margin: 0 0 36px 0;
                    font-size: 1.1rem;
                    font-weight: 400;
                    color: rgba(255, 255, 255, 0.6);
                    letter-spacing: 0.2em;
                    text-align: center;
                }

                /* ── 소셜 로그인 ── */
                .social-buttons {
                    display: flex;
                    justify-content: center;
                    gap: 24px;
                    margin-bottom: 32px;
                }

                .social-btn {
                    width: 56px;
                    height: 56px;
                    border-radius: 50%;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    background: rgba(255, 255, 255, 0.03);
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 0;
                    transition: all 0.3s ease;
                    overflow: hidden;
                }

                .social-btn:hover {
                    border-color: rgba(255, 255, 255, 0.2);
                    transform: translateY(-3px);
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
                }

                .social-btn.kakao:hover {
                    border-color: rgba(254, 229, 0, 0.4);
                    box-shadow: 0 8px 24px rgba(254, 229, 0, 0.08);
                }

                .social-btn.naver:hover {
                    border-color: rgba(3, 199, 90, 0.4);
                    box-shadow: 0 8px 24px rgba(3, 199, 90, 0.08);
                }

                .social-btn.google:hover {
                    border-color: rgba(66, 133, 244, 0.4);
                    box-shadow: 0 8px 24px rgba(66, 133, 244, 0.08);
                }

                /* ── 잠김/연동 상태 ── */
                .social-btn-wrap {
                    position: relative;
                    display: inline-block;
                }

                .social-btn-locked {
                    opacity: 0.3;
                    filter: grayscale(0.8);
                    cursor: not-allowed !important;
                }
                .social-btn-locked:hover {
                    transform: none;
                    box-shadow: none;
                    border-color: rgba(255, 255, 255, 0.08);
                }

                .social-btn-linked {
                    border-color: rgba(255, 255, 255, 0.15);
                }

                .linked-dot {
                    position: absolute;
                    bottom: -2px;
                    right: -2px;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    border: 2px solid #000;
                }
                .kakao-dot { background: #FEE500; }
                .naver-dot { background: #03C75A; }
                .google-dot { background: #4285F4; }

                /* ── 토스트 메시지 ── */
                .toast-message {
                    position: fixed;
                    top: 24px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(30, 30, 30, 0.95);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    color: rgba(255, 255, 255, 0.85);
                    padding: 12px 24px;
                    border-radius: 10px;
                    font-size: 0.82rem;
                    backdrop-filter: blur(12px);
                    z-index: 100;
                    animation: toastIn 0.3s ease-out;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    white-space: nowrap;
                }
                .toast-icon { font-size: 1rem; }
                @keyframes toastIn {
                    from { opacity: 0; transform: translateX(-50%) translateY(-12px); }
                    to { opacity: 1; transform: translateX(-50%) translateY(0); }
                }

                /* ── 연동 안내 ── */
                .link-hint {
                    text-align: center;
                    font-size: 0.7rem;
                    color: rgba(255, 255, 255, 0.25);
                    margin: 0 0 8px 0;
                }
                .link-hint-anchor {
                    color: rgba(96, 165, 250, 0.7);
                    text-decoration: underline;
                    text-underline-offset: 2px;
                }
                .link-hint-anchor:hover {
                    color: rgba(96, 165, 250, 1);
                }


                .social-icon {
                    width: 28px;
                    height: 28px;
                    object-fit: contain;
                }

                /* ── 구분선 ── */
                .divider {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    margin-bottom: 28px;
                }

                .divider-line {
                    flex: 1;
                    height: 1px;
                    background: rgba(255, 255, 255, 0.06);
                }

                .divider-text {
                    font-size: 0.7rem;
                    color: rgba(255, 255, 255, 0.2);
                    letter-spacing: 0.1em;
                }

                /* ── 게스트 버튼 ── */
                .guest-btn {
                    position: relative;
                    display: block;
                    width: 100%;
                    padding: 14px 0;
                    background: transparent;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    color: rgba(255, 255, 255, 0.35);
                    font-size: 0.85rem;
                    font-family: inherit;
                    letter-spacing: 0.2em;
                    text-decoration: none;
                    text-align: center;
                    cursor: pointer;
                    overflow: hidden;
                    transition: all 0.4s ease;
                }

                .guest-btn:hover {
                    color: rgba(255, 255, 255, 0.8);
                    border-color: rgba(255, 255, 255, 0.15);
                }

                .guest-btn-text {
                    position: relative;
                    z-index: 1;
                }

                .guest-btn:hover .guest-btn-text {
                    animation: textSparkle 1.2s ease-in-out;
                }

                @keyframes textSparkle {
                    0% {
                        text-shadow: 0 0 0 transparent;
                    }
                    25% {
                        text-shadow:
                            0 0 8px rgba(255, 255, 255, 0.6),
                            0 0 20px rgba(255, 255, 255, 0.3);
                    }
                    50% {
                        text-shadow:
                            0 0 15px rgba(255, 255, 255, 0.8),
                            0 0 40px rgba(255, 255, 255, 0.4),
                            0 0 60px rgba(255, 255, 255, 0.15);
                    }
                    75% {
                        text-shadow:
                            0 0 8px rgba(255, 255, 255, 0.4),
                            0 0 20px rgba(255, 255, 255, 0.2);
                    }
                    100% {
                        text-shadow: 0 0 0 transparent;
                    }
                }

                .guest-btn-line {
                    position: absolute;
                    bottom: 0;
                    left: 50%;
                    transform: translateX(-50%);
                    width: 0;
                    height: 1px;
                    background: linear-gradient(
                        90deg,
                        transparent,
                        rgba(255, 255, 255, 0.4),
                        transparent
                    );
                    transition: width 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                }

                .guest-btn:hover .guest-btn-line {
                    width: 80%;
                }

                /* ── 하단 링크 ── */
                .login-footer {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-top: 24px;
                }

                .footer-link {
                    color: rgba(255, 255, 255, 0.2);
                    font-size: 0.75rem;
                    font-weight: 300;
                    letter-spacing: 0.1em;
                    text-decoration: none;
                    transition: color 0.3s ease;
                }

                .footer-link:hover {
                    color: rgba(255, 255, 255, 0.6);
                }

                /* ── 애니메이션 ── */
                @keyframes fadeIn {
                    from {
                        opacity: 0;
                    }
                    to {
                        opacity: 1;
                    }
                }

                @keyframes fadeInUp {
                    from {
                        opacity: 0;
                        transform: translateY(24px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                /* ── 모바일 반응형 ── */
                @media (max-width: 640px) {
                    .logo {
                        margin-bottom: 36px;
                    }
                    .logo-char {
                        font-size: 1.6rem;
                    }
                    .login-card {
                        padding: 32px 24px;
                    }
                    .login-title {
                        font-size: 1rem;
                        margin-bottom: 28px;
                    }
                    .social-buttons {
                        gap: 18px;
                        margin-bottom: 24px;
                    }
                    .social-btn {
                        width: 48px;
                        height: 48px;
                    }
                    .social-icon {
                        width: 24px;
                        height: 24px;
                    }
                    .divider {
                        gap: 12px;
                        margin-bottom: 22px;
                    }
                    .guest-btn {
                        padding: 12px 0;
                        font-size: 0.8rem;
                    }
                }

                @media (max-width: 360px) {
                    .login-card {
                        padding: 28px 20px;
                        width: min(340px, 90vw);
                    }
                    .social-btn {
                        width: 44px;
                        height: 44px;
                    }
                    .social-icon {
                        width: 20px;
                        height: 20px;
                    }
                }

                /* 가로 모드 대응 */
                @media (max-height: 500px) {
                    .logo {
                        margin-bottom: 16px;
                    }
                    .login-card {
                        padding: 20px 24px;
                    }
                    .login-title {
                        margin-bottom: 16px;
                    }
                    .social-buttons {
                        margin-bottom: 16px;
                    }
                    .divider {
                        margin-bottom: 16px;
                    }
                }
            `}</style>
        </div>
    );
}
