"use client";

const PARTICLES = [
    { left: "5%", delay: "0s", duration: "7s", opacity: 0.2 },
    { left: "15%", delay: "4s", duration: "11s", opacity: 0.18 },
    { left: "28%", delay: "5s", duration: "10s", opacity: 0.35 },
    { left: "38%", delay: "7s", duration: "7.5s", opacity: 0.28 },
    { left: "48%", delay: "6s", duration: "8.5s", opacity: 0.32 },
    { left: "58%", delay: "4.5s", duration: "13s", opacity: 0.26 },
    { left: "68%", delay: "7.5s", duration: "10s", opacity: 0.2 },
    { left: "77%", delay: "5.5s", duration: "9s", opacity: 0.24 },
    { left: "86%", delay: "6.5s", duration: "7.8s", opacity: 0.33 },
    { left: "94%", delay: "4.2s", duration: "9.2s", opacity: 0.27 },
];

export default function TestExamPage() {
    return (
        <div className="exam-container">
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

            {/* 상단 로고 */}
            <a href="/" className="top-logo">
                <span>공</span><span>잘</span><span>알</span>
            </a>

            {/* 메인 콘텐츠 */}
            <div className="content">
                <h1 className="title">가상 모의고사</h1>

                <div className="buttons">
                    <a href="/test_exam/select" className="exam-btn">
                        <span className="exam-btn-text">선택해서 풀기</span>
                        <span className="exam-btn-line" />
                    </a>
                    <a href="/test_exam/random" className="exam-btn">
                        <span className="exam-btn-text">랜덤으로 풀기</span>
                        <span className="exam-btn-line" />
                    </a>
                </div>

                <div className="descriptions">
                    <div className="desc-item">
                        <span className="desc-label">선택해서 풀기</span>
                        <p className="desc-text">풀고자 하는 년도의 과목을 지정하고, 시간을 재면서 총 20문제를 순서대로 풀어보기</p>
                    </div>
                    <div className="desc-item">
                        <span className="desc-label">랜덤으로 풀기</span>
                        <p className="desc-text">년도와 과목 상관없이 무작위로 문제가 나오고, 풀이 시간을 기록하면서 풀어보기</p>
                    </div>
                </div>
            </div>

            {/* 하단 네비게이션 */}
            <div className="bottom-nav">
                <a href="/chat" className="nav-link">채팅으로</a>
                <span className="nav-divider">·</span>
                <a href="/" className="nav-link">홈으로</a>
            </div>

            <style jsx>{`
                .exam-container {
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
                    10% { opacity: 0.4; }
                    90% { opacity: 0.1; }
                    100% {
                        transform: translateY(-100vh) scale(0.3);
                        opacity: 0;
                    }
                }

                /* ── 상단 로고 ── */
                .top-logo {
                    position: absolute;
                    top: 28px;
                    left: 32px;
                    display: flex;
                    gap: 2px;
                    text-decoration: none;
                    font-size: 1.2rem;
                    font-weight: 900;
                    color: #fff;
                    letter-spacing: 0.05em;
                    z-index: 10;
                }

                /* ── 메인 콘텐츠 ── */
                .content {
                    position: relative;
                    z-index: 1;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    animation: fadeInUp 0.8s ease-out;
                }

                .title {
                    font-size: 1.8rem;
                    font-weight: 700;
                    color: rgba(255, 255, 255, 0.9);
                    letter-spacing: 0.15em;
                    margin: 0 0 56px 0;
                    text-shadow: 0 0 30px rgba(255, 255, 255, 0.08);
                }

                /* ── 버튼 ── */
                .buttons {
                    display: flex;
                    gap: 32px;
                    margin-bottom: 64px;
                }

                .exam-btn {
                    position: relative;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 200px;
                    height: 56px;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    background: rgba(255, 255, 255, 0.02);
                    backdrop-filter: blur(8px);
                    text-decoration: none;
                    cursor: pointer;
                    overflow: hidden;
                    transition: all 0.4s ease;
                }

                .exam-btn:hover {
                    border-color: rgba(255, 255, 255, 0.2);
                    background: rgba(255, 255, 255, 0.05);
                    transform: translateY(-2px);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                }

                .exam-btn-text {
                    position: relative;
                    z-index: 1;
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 0.9rem;
                    font-weight: 500;
                    letter-spacing: 0.12em;
                    transition: all 0.4s ease;
                }

                .exam-btn:hover .exam-btn-text {
                    color: rgba(255, 255, 255, 0.95);
                    animation: textSparkle 1.2s ease-in-out;
                }

                .exam-btn-line {
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
                    transition: width 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                }

                .exam-btn:hover .exam-btn-line {
                    width: 80%;
                }

                @keyframes textSparkle {
                    0% { text-shadow: 0 0 0 transparent; }
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
                    100% { text-shadow: 0 0 0 transparent; }
                }

                /* ── 설명 ── */
                .descriptions {
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                    max-width: 520px;
                }

                .desc-item {
                    padding: 16px 20px;
                    border-radius: 10px;
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.04);
                }

                .desc-label {
                    display: inline-block;
                    font-size: 0.8rem;
                    font-weight: 600;
                    color: rgba(255, 255, 255, 0.6);
                    letter-spacing: 0.08em;
                    margin-bottom: 6px;
                }

                .desc-text {
                    margin: 0;
                    font-size: 0.78rem;
                    color: rgba(255, 255, 255, 0.3);
                    line-height: 1.7;
                    letter-spacing: 0.02em;
                }

                /* ── 하단 네비게이션 ── */
                .bottom-nav {
                    position: absolute;
                    bottom: 32px;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    z-index: 10;
                }

                .nav-link {
                    color: rgba(255, 255, 255, 0.2);
                    font-size: 0.72rem;
                    letter-spacing: 0.05em;
                    text-decoration: none;
                    transition: color 0.2s ease;
                }

                .nav-link:hover {
                    color: rgba(255, 255, 255, 0.6);
                }

                .nav-divider {
                    color: rgba(255, 255, 255, 0.1);
                    font-size: 0.7rem;
                }

                /* ── 애니메이션 ── */
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

                /* ── 모바일 대응 ── */
                @media (max-width: 520px) {
                    .buttons {
                        flex-direction: column;
                        gap: 16px;
                    }
                    .exam-btn {
                        width: 240px;
                    }
                    .title {
                        font-size: 1.4rem;
                    }
                    .descriptions {
                        padding: 0 20px;
                    }
                }
            `}</style>
        </div>
    );
}

