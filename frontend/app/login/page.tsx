"use client";

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

export default function LoginPage() {
    return (
        <div className="login-container">
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
                    <button className="social-btn kakao" onClick={() => { /* TODO: 카카오 로그인 */ }}>
                        <img src="/images/login/kakao.png" alt="카카오 로그인" className="social-icon" />
                    </button>
                    <button className="social-btn naver" onClick={() => { /* TODO: 네이버 로그인 */ }}>
                        <img src="/images/login/naver.png" alt="네이버 로그인" className="social-icon" />
                    </button>
                    <button className="social-btn google" onClick={() => { /* TODO: 구글 로그인 */ }}>
                        <img src="/images/login/google.png" alt="구글 로그인" className="social-icon" />
                    </button>
                </div>

                {/* 구분선 */}
                <div className="divider">
                    <span className="divider-line" />
                    <span className="divider-text">또는</span>
                    <span className="divider-line" />
                </div>

                {/* 게스트 입장 버튼 */}
                <a href="/chat" className="guest-btn">
                    <span className="guest-btn-text">게스트로 입장하기</span>
                    <span className="guest-btn-line" />
                </a>

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
