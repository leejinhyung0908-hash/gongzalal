"use client";

// 서버/클라이언트 동일한 고정 파티클 데이터 (hydration 불일치 방지)
const PARTICLES = [
    { left: "5%", delay: "0s", duration: "7s", opacity: 0.2 },
    { left: "10%", delay: "2s", duration: "9s", opacity: 0.3 },
    { left: "15%", delay: "4s", duration: "11s", opacity: 0.18 },
    { left: "20%", delay: "1s", duration: "8s", opacity: 0.25 },
    { left: "28%", delay: "5s", duration: "10s", opacity: 0.35 },
    { left: "33%", delay: "3s", duration: "12s", opacity: 0.2 },
    { left: "38%", delay: "7s", duration: "7.5s", opacity: 0.28 },
    { left: "42%", delay: "0.5s", duration: "9.5s", opacity: 0.22 },
    { left: "48%", delay: "6s", duration: "8.5s", opacity: 0.32 },
    { left: "53%", delay: "2.5s", duration: "11s", opacity: 0.17 },
    { left: "58%", delay: "4.5s", duration: "13s", opacity: 0.26 },
    { left: "63%", delay: "1.5s", duration: "7s", opacity: 0.38 },
    { left: "68%", delay: "7.5s", duration: "10s", opacity: 0.2 },
    { left: "72%", delay: "3.5s", duration: "8s", opacity: 0.3 },
    { left: "77%", delay: "5.5s", duration: "9s", opacity: 0.24 },
    { left: "82%", delay: "0.8s", duration: "12s", opacity: 0.16 },
    { left: "86%", delay: "6.5s", duration: "7.8s", opacity: 0.33 },
    { left: "90%", delay: "2.8s", duration: "10.5s", opacity: 0.21 },
    { left: "94%", delay: "4.2s", duration: "9.2s", opacity: 0.27 },
    { left: "97%", delay: "1.8s", duration: "11.5s", opacity: 0.19 },
];

export default function MainPage() {
    return (
        <div className="main-container">
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

            {/* 메인 타이틀 */}
            <div className="title-wrapper">
                <h1 className="title">
                    <span className="char char-1">공</span>
                    <span className="char char-2">잘</span>
                    <span className="char char-3">알</span>
                </h1>
                <div className="glow" />
            </div>

            {/* 시작하기 버튼 */}
            <a href="/login" className="start-btn">
                <span className="start-btn-text">시작하기</span>
                <span className="start-btn-line" />
                <span className="start-btn-shimmer" />
            </a>

            {/* 하단 서브텍스트 */}
            <p className="subtitle">공무원 시험, 잘 알려주는 AI</p>

            <style jsx>{`
                .main-container {
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

                /* ── 배경 파티클 ── */
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

                /* ── 타이틀 래퍼 ── */
                .title-wrapper {
                    position: relative;
                    animation: float 4s ease-in-out infinite;
                }

                @keyframes float {
                    0%,
                    100% {
                        transform: translateY(0px);
                    }
                    50% {
                        transform: translateY(-20px);
                    }
                }

                /* ── 글로우 효과 ── */
                .glow {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: 200px;
                    height: 300px;
                    background: radial-gradient(
                        ellipse at center,
                        rgba(255, 255, 255, 0.06) 0%,
                        rgba(255, 255, 255, 0.02) 40%,
                        transparent 70%
                    );
                    border-radius: 50%;
                    pointer-events: none;
                    animation: pulse 4s ease-in-out infinite;
                }

                @keyframes pulse {
                    0%,
                    100% {
                        opacity: 0.6;
                        transform: translate(-50%, -50%) scale(1);
                    }
                    50% {
                        opacity: 1;
                        transform: translate(-50%, -50%) scale(1.2);
                    }
                }

                /* ── 세로 타이틀 ── */
                .title {
                    writing-mode: vertical-rl;
                    text-orientation: upright;
                    font-size: clamp(4rem, 10vw, 8rem);
                    font-weight: 900;
                    color: #fff;
                    letter-spacing: 0.3em;
                    margin: 0;
                    text-shadow:
                        0 0 20px rgba(255, 255, 255, 0.15),
                        0 0 60px rgba(255, 255, 255, 0.05);
                    user-select: none;
                }

                /* ── 글자별 애니메이션 ── */
                .char {
                    display: inline-block;
                    animation: charGlow 3s ease-in-out infinite;
                }

                .char-1 {
                    animation-delay: 0s;
                }
                .char-2 {
                    animation-delay: 0.4s;
                }
                .char-3 {
                    animation-delay: 0.8s;
                }

                @keyframes charGlow {
                    0%,
                    100% {
                        text-shadow:
                            0 0 10px rgba(255, 255, 255, 0.1),
                            0 0 30px rgba(255, 255, 255, 0.05);
                        opacity: 0.85;
                    }
                    50% {
                        text-shadow:
                            0 0 20px rgba(255, 255, 255, 0.3),
                            0 0 60px rgba(255, 255, 255, 0.1),
                            0 0 100px rgba(255, 255, 255, 0.05);
                        opacity: 1;
                    }
                }

                /* ── 시작하기 버튼 ── */
                .start-btn {
                    position: relative;
                    display: inline-block;
                    margin-top: 48px;
                    padding: 12px 0;
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 1rem;
                    font-weight: 400;
                    letter-spacing: 0.3em;
                    text-decoration: none;
                    cursor: pointer;
                    overflow: hidden;
                    transition: color 0.4s ease;
                    animation: fadeInUp 2s ease-out 1s both;
                }

                .start-btn:hover {
                    color: rgba(255, 255, 255, 1);
                }

                .start-btn-text {
                    position: relative;
                    z-index: 1;
                }

                /* 밑줄 효과 */
                .start-btn-line {
                    position: absolute;
                    bottom: 0;
                    left: 50%;
                    transform: translateX(-50%);
                    width: 0;
                    height: 1px;
                    background: linear-gradient(
                        90deg,
                        transparent,
                        rgba(255, 255, 255, 0.8),
                        transparent
                    );
                    transition: width 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                }

                .start-btn:hover .start-btn-line {
                    width: 100%;
                }

                /* 반짝이 효과 - 글자에만 적용 */
                .start-btn-shimmer {
                    display: none;
                }

                .start-btn:hover .start-btn-text {
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

                /* ── 서브텍스트 ── */
                .subtitle {
                    position: absolute;
                    bottom: 60px;
                    color: rgba(255, 255, 255, 0.3);
                    font-size: 0.85rem;
                    font-weight: 300;
                    letter-spacing: 0.5em;
                    animation: fadeInUp 2s ease-out 0.5s both;
                }

                @keyframes fadeInUp {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                /* ── 모바일 반응형 ── */
                @media (max-width: 640px) {
                    .title {
                        font-size: clamp(3rem, 14vw, 5rem);
                        letter-spacing: 0.2em;
                    }
                    .glow {
                        width: 150px;
                        height: 220px;
                    }
                    .start-btn {
                        margin-top: 36px;
                        font-size: 0.9rem;
                        letter-spacing: 0.2em;
                    }
                    .subtitle {
                        bottom: 40px;
                        font-size: 0.7rem;
                        letter-spacing: 0.3em;
                    }
                }

                @media (max-width: 360px) {
                    .title {
                        font-size: clamp(2.5rem, 16vw, 4rem);
                    }
                    .subtitle {
                        bottom: 30px;
                        font-size: 0.6rem;
                        letter-spacing: 0.2em;
                    }
                }

                /* 가로 모드 대응 */
                @media (max-height: 500px) {
                    .title {
                        font-size: clamp(2rem, 8vh, 4rem);
                    }
                    .start-btn {
                        margin-top: 20px;
                    }
                    .subtitle {
                        bottom: 16px;
                        font-size: 0.65rem;
                    }
                }
            `}</style>
        </div>
    );
}

