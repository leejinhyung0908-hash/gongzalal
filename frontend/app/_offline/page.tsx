"use client";

export default function OfflinePage() {
    return (
        <div className="offline-container">
            {/* 배경 격자 */}
            <div className="grid-bg" />

            {/* 메인 콘텐츠 */}
            <div className="offline-content">
                <div className="offline-icon">
                    <svg
                        width="64"
                        height="64"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <line x1="1" y1="1" x2="23" y2="23" />
                        <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" />
                        <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" />
                        <path d="M10.71 5.05A16 16 0 0 1 22.56 9" />
                        <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" />
                        <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
                        <line x1="12" y1="20" x2="12.01" y2="20" />
                    </svg>
                </div>

                <h1 className="offline-title">오프라인 상태</h1>
                <p className="offline-desc">
                    인터넷 연결이 끊어졌습니다.<br />
                    네트워크 연결을 확인해 주세요.
                </p>

                <button
                    className="retry-btn"
                    onClick={() => window.location.reload()}
                >
                    <span className="retry-text">다시 시도</span>
                    <span className="retry-line" />
                </button>

                <div className="offline-footer">
                    <span className="footer-logo">공잘알</span>
                    <span className="footer-dot">·</span>
                    <span className="footer-sub">공무원 시험, 잘 알려주는 AI</span>
                </div>
            </div>

            <style jsx>{`
                .offline-container {
                    position: relative;
                    width: 100vw;
                    height: 100vh;
                    background: #000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                    font-family:
                        "Gothic A1",
                        "Noto Sans KR",
                        "Malgun Gothic",
                        sans-serif;
                }

                .grid-bg {
                    position: absolute;
                    inset: 0;
                    background-image:
                        linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
                    background-size: 40px 40px;
                    pointer-events: none;
                }

                .offline-content {
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    text-align: center;
                    padding: 40px 24px;
                    animation: fadeIn 0.8s ease-out;
                }

                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(16px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                .offline-icon {
                    color: rgba(255, 255, 255, 0.15);
                    margin-bottom: 28px;
                    animation: pulse 3s ease-in-out infinite;
                }

                @keyframes pulse {
                    0%, 100% { opacity: 0.6; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.05); }
                }

                .offline-title {
                    font-size: 1.4rem;
                    font-weight: 700;
                    color: rgba(255, 255, 255, 0.8);
                    letter-spacing: 0.1em;
                    margin: 0 0 14px 0;
                }

                .offline-desc {
                    font-size: 0.85rem;
                    color: rgba(255, 255, 255, 0.3);
                    line-height: 1.7;
                    margin: 0 0 40px 0;
                    letter-spacing: 0.02em;
                }

                .retry-btn {
                    position: relative;
                    padding: 12px 36px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    background: rgba(255, 255, 255, 0.03);
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 0.85rem;
                    font-family: inherit;
                    letter-spacing: 0.15em;
                    cursor: pointer;
                    overflow: hidden;
                    transition: all 0.3s ease;
                }

                .retry-btn:hover {
                    color: rgba(255, 255, 255, 0.9);
                    border-color: rgba(255, 255, 255, 0.2);
                    background: rgba(255, 255, 255, 0.05);
                }

                .retry-btn:active {
                    transform: scale(0.97);
                }

                .retry-text {
                    position: relative;
                    z-index: 1;
                }

                .retry-line {
                    position: absolute;
                    bottom: 0;
                    left: 50%;
                    transform: translateX(-50%);
                    width: 0;
                    height: 1px;
                    background: linear-gradient(
                        90deg,
                        transparent,
                        rgba(255, 255, 255, 0.5),
                        transparent
                    );
                    transition: width 0.4s ease;
                }

                .retry-btn:hover .retry-line {
                    width: 80%;
                }

                .offline-footer {
                    position: absolute;
                    bottom: -80px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .footer-logo {
                    font-size: 0.75rem;
                    font-weight: 700;
                    color: rgba(255, 255, 255, 0.2);
                    letter-spacing: 0.1em;
                }

                .footer-dot {
                    color: rgba(255, 255, 255, 0.1);
                    font-size: 0.7rem;
                }

                .footer-sub {
                    font-size: 0.65rem;
                    color: rgba(255, 255, 255, 0.12);
                    letter-spacing: 0.1em;
                }

                /* ── 모바일 반응형 ── */
                @media (max-width: 640px) {
                    .offline-icon svg {
                        width: 48px;
                        height: 48px;
                    }
                    .offline-title {
                        font-size: 1.15rem;
                    }
                    .offline-desc {
                        font-size: 0.78rem;
                        margin-bottom: 32px;
                    }
                    .retry-btn {
                        padding: 10px 28px;
                        font-size: 0.8rem;
                    }
                }
            `}</style>
        </div>
    );
}

