"use client";

import { useEffect, useRef, useState } from "react";

const FEATURES = [
    {
        icon: (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
        ),
        label: "AI 멘토 채팅",
        desc: "합격 수기 4,910건을 학습한 AI가\n실제 합격자처럼 맞춤 조언을 드립니다.",
        detail: "시험 과목 선택 · 공부법 · 교재 추천",
        accent: "rgba(99,102,241,0.8)",
        bg: "rgba(99,102,241,0.06)",
        border: "rgba(99,102,241,0.15)",
    },
    {
        icon: (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
            </svg>
        ),
        label: "가상 모의고사",
        desc: "실전과 동일한 환경에서\n시험 감각을 키워보세요.",
        detail: "타이머 · 자동 채점 · 오답 분석",
        accent: "rgba(52,211,153,0.8)",
        bg: "rgba(52,211,153,0.06)",
        border: "rgba(52,211,153,0.15)",
    },
    {
        icon: (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
                <path d="M8 14h.01" /><path d="M12 14h.01" /><path d="M16 14h.01" />
                <path d="M8 18h.01" /><path d="M12 18h.01" />
            </svg>
        ),
        label: "AI 학습 계획",
        desc: "나의 목표와 현재 실력을 분석해\nAI가 최적의 학습 플랜을 생성합니다.",
        detail: "단계별 커리큘럼 · 과목별 비중 · 일정 관리",
        accent: "rgba(251,191,36,0.8)",
        bg: "rgba(251,191,36,0.06)",
        border: "rgba(251,191,36,0.15)",
    },
    {
        icon: (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16 16 12 12 8 16" />
                <line x1="12" y1="12" x2="12" y2="21" />
                <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
            </svg>
        ),
        label: "자료 업로드",
        desc: "해설지, 문제지를 업로드하면\nAI가 자동으로 분석해 데이터베이스에 추가합니다.",
        detail: "PDF · 이미지 · 자동 분류",
        accent: "rgba(244,114,182,0.8)",
        bg: "rgba(244,114,182,0.06)",
        border: "rgba(244,114,182,0.15)",
    },
];

const STATS = [
    { value: "4,910", label: "합격 수기" },
    { value: "AI", label: "맞춤 분석" },
    { value: "24/7", label: "언제나 이용" },
    { value: "무료", label: "베타 서비스" },
];

function useInView(threshold = 0.15) {
    const ref = useRef<HTMLDivElement>(null);
    const [visible, setVisible] = useState(false);
    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        const obs = new IntersectionObserver(
            ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect(); } },
            { threshold }
        );
        obs.observe(el);
        return () => obs.disconnect();
    }, [threshold]);
    return { ref, visible };
}

const STEPS = [
    { num: "01", title: "로그인", desc: "카카오, 네이버, 구글 소셜 로그인으로 3초 만에 시작" },
    { num: "02", title: "AI 멘토와 대화", desc: "공부법, 교재, 일정 등 무엇이든 물어보세요" },
    { num: "03", title: "학습 계획 생성", desc: "AI가 분석한 나만의 맞춤 커리큘럼을 확인하세요" },
];

function StepItem({ step, index }: { step: typeof STEPS[0]; index: number }) {
    const { ref, visible } = useInView();
    return (
        <div
            ref={ref}
            className="step-item"
            style={{
                opacity: visible ? 1 : 0,
                transform: visible ? "translateX(0)" : "translateX(-24px)",
                transition: `opacity 0.6s ease ${index * 0.15}s, transform 0.6s ease ${index * 0.15}s`,
            }}
        >
            <span className="step-num">{step.num}</span>
            <div className="step-body">
                <h3 className="step-title">{step.title}</h3>
                <p className="step-desc">{step.desc}</p>
            </div>
            {index < 2 && <div className="step-connector" />}
        </div>
    );
}

function FeatureCard({ feature, index }: { feature: typeof FEATURES[0]; index: number }) {
    const { ref, visible } = useInView();
    return (
        <div
            ref={ref}
            className="feature-card"
            style={{
                opacity: visible ? 1 : 0,
                transform: visible ? "translateY(0)" : "translateY(32px)",
                transition: `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`,
                background: feature.bg,
                borderColor: feature.border,
            }}
        >
            <div className="feature-icon" style={{ color: feature.accent }}>
                {feature.icon}
            </div>
            <h3 className="feature-label" style={{ color: feature.accent }}>{feature.label}</h3>
            <p className="feature-desc">{feature.desc}</p>
            <span className="feature-detail">{feature.detail}</span>
        </div>
    );
}

export default function AboutPage() {
    const heroRef = useRef<HTMLDivElement>(null);
    const statsSection = useInView();
    const ctaSection = useInView();

    // 스크롤 패럴랙스
    useEffect(() => {
        const handleScroll = () => {
            if (heroRef.current) {
                heroRef.current.style.transform = `translateY(${window.scrollY * 0.3}px)`;
            }
        };
        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    return (
        <div className="about-wrap">
            {/* ── 상단 내비게이션 ── */}
            <nav className="top-nav">
                <a href="/" className="nav-logo">공잘알</a>
                <a href="/login" className="nav-cta">시작하기 →</a>
            </nav>

            {/* ── 히어로 섹션 ── */}
            <section className="hero-section">
                <div className="hero-bg" ref={heroRef}>
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="hero-orb" style={{
                            left: `${15 + i * 15}%`,
                            animationDelay: `${i * 1.2}s`,
                            width: `${180 + i * 40}px`,
                            height: `${180 + i * 40}px`,
                        }} />
                    ))}
                </div>
                <div className="hero-content">
                    <p className="hero-eyebrow">공무원 시험 AI 플랫폼</p>
                    <h1 className="hero-title">
                        합격의 길,<br />
                        <span className="hero-title-accent">공잘알</span>이 함께합니다
                    </h1>
                    <p className="hero-sub">
                        실제 합격자 4,910명의 경험을 AI가 분석해<br />
                        나만의 맞춤형 공부법을 알려드립니다
                    </p>
                    <div className="hero-actions">
                        <a href="/login" className="btn-primary">무료로 시작하기</a>
                        <a href="/chat" className="btn-ghost">게스트로 체험하기</a>
                    </div>
                </div>
                <div className="hero-scroll-hint">
                    <span>스크롤</span>
                    <div className="scroll-arrow" />
                </div>
            </section>

            {/* ── 통계 섹션 ── */}
            <section
                ref={statsSection.ref}
                className="stats-section"
                style={{
                    opacity: statsSection.visible ? 1 : 0,
                    transform: statsSection.visible ? "translateY(0)" : "translateY(24px)",
                    transition: "opacity 0.7s ease, transform 0.7s ease",
                }}
            >
                <div className="stats-grid">
                    {STATS.map((s, i) => (
                        <div key={i} className="stat-item">
                            <span className="stat-value">{s.value}</span>
                            <span className="stat-label">{s.label}</span>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── 섹션 구분선 ── */}
            <div className="section-divider" />

            {/* ── 주요 기능 ── */}
            <section className="features-section">
                <div className="section-header">
                    <p className="section-eyebrow">핵심 기능</p>
                    <h2 className="section-title">공시 합격을 위한<br />모든 것이 한 곳에</h2>
                </div>
                <div className="features-grid">
                    {FEATURES.map((f, i) => (
                        <FeatureCard key={i} feature={f} index={i} />
                    ))}
                </div>
            </section>

            {/* ── 섹션 구분선 ── */}
            <div className="section-divider" />

            {/* ── 어떻게 작동하나요 ── */}
            <section className="how-section">
                <div className="section-header">
                    <p className="section-eyebrow">이용 방법</p>
                    <h2 className="section-title">3단계로 시작하세요</h2>
                </div>
                <div className="steps-list">
                    {STEPS.map((step, i) => (
                        <StepItem key={i} step={step} index={i} />
                    ))}
                </div>
            </section>

            {/* ── CTA 섹션 ── */}
            <section
                ref={ctaSection.ref}
                className="cta-section"
                style={{
                    opacity: ctaSection.visible ? 1 : 0,
                    transform: ctaSection.visible ? "translateY(0)" : "translateY(32px)",
                    transition: "opacity 0.7s ease, transform 0.7s ease",
                }}
            >
                <div className="cta-glow" />
                <p className="cta-eyebrow">지금 바로</p>
                <h2 className="cta-title">합격의 첫 걸음을<br />시작하세요</h2>
                <a href="/login" className="btn-primary btn-large">무료로 시작하기</a>
                <p className="cta-note">별도 설치 없이 브라우저에서 바로 이용 가능합니다</p>
            </section>

            {/* ── 푸터 ── */}
            <footer className="about-footer">
                <a href="/" className="footer-logo">공잘알</a>
                <p className="footer-copy">공무원 시험, 잘 알려주는 AI</p>
            </footer>

            <style jsx>{`
                * { box-sizing: border-box; }

                .about-wrap {
                    min-height: 100vh;
                    background: #000;
                    color: #fff;
                    font-family: "Gothic A1", "Noto Sans KR", "Malgun Gothic", sans-serif;
                    overflow-x: hidden;
                }

                /* ── 내비게이션 ── */
                .top-nav {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    z-index: 100;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 20px 40px;
                    background: rgba(0,0,0,0.6);
                    backdrop-filter: blur(16px);
                    border-bottom: 1px solid rgba(255,255,255,0.04);
                }
                .nav-logo {
                    font-size: 1.2rem;
                    font-weight: 900;
                    color: #fff;
                    text-decoration: none;
                    letter-spacing: 0.05em;
                }
                .nav-cta {
                    font-size: 0.82rem;
                    font-weight: 500;
                    color: rgba(255,255,255,0.5);
                    text-decoration: none;
                    letter-spacing: 0.1em;
                    transition: color 0.3s ease;
                }
                .nav-cta:hover { color: #fff; }

                /* ── 히어로 ── */
                .hero-section {
                    position: relative;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                    padding: 120px 24px 80px;
                }
                .hero-bg {
                    position: absolute;
                    inset: 0;
                    pointer-events: none;
                }
                .hero-orb {
                    position: absolute;
                    top: 50%;
                    border-radius: 50%;
                    background: radial-gradient(ellipse at center, rgba(255,255,255,0.025) 0%, transparent 70%);
                    transform: translateY(-50%);
                    animation: orbPulse 8s ease-in-out infinite;
                }
                @keyframes orbPulse {
                    0%, 100% { opacity: 0.4; transform: translateY(-50%) scale(1); }
                    50% { opacity: 0.8; transform: translateY(-50%) scale(1.08); }
                }
                .hero-content {
                    position: relative;
                    z-index: 1;
                    text-align: center;
                    max-width: 680px;
                    animation: heroFadeIn 1.2s ease-out both;
                }
                @keyframes heroFadeIn {
                    from { opacity: 0; transform: translateY(28px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .hero-eyebrow {
                    font-size: 0.78rem;
                    font-weight: 400;
                    color: rgba(255,255,255,0.35);
                    letter-spacing: 0.35em;
                    text-transform: uppercase;
                    margin: 0 0 24px;
                    animation: heroFadeIn 1.2s ease-out 0.1s both;
                }
                .hero-title {
                    font-size: clamp(2.2rem, 6vw, 4rem);
                    font-weight: 900;
                    line-height: 1.2;
                    margin: 0 0 12px;
                    color: rgba(255,255,255,0.92);
                    letter-spacing: -0.01em;
                    animation: heroFadeIn 1.2s ease-out 0.2s both;
                }
                .hero-title-accent {
                    color: rgba(255,255,255,1);
                    text-shadow:
                        0 0 20px rgba(255,255,255,0.2),
                        0 0 60px rgba(255,255,255,0.08);
                }
                .hero-sub {
                    font-size: clamp(0.9rem, 2vw, 1.05rem);
                    font-weight: 300;
                    color: rgba(255,255,255,0.4);
                    line-height: 1.8;
                    margin: 0 0 48px;
                    letter-spacing: 0.02em;
                    animation: heroFadeIn 1.2s ease-out 0.3s both;
                }
                .hero-actions {
                    display: flex;
                    gap: 16px;
                    justify-content: center;
                    flex-wrap: wrap;
                    animation: heroFadeIn 1.2s ease-out 0.4s both;
                }

                /* ── 버튼 ── */
                .btn-primary {
                    display: inline-block;
                    padding: 14px 32px;
                    background: rgba(255,255,255,0.95);
                    color: #000;
                    font-size: 0.9rem;
                    font-weight: 700;
                    letter-spacing: 0.08em;
                    text-decoration: none;
                    border-radius: 8px;
                    transition: all 0.3s ease;
                }
                .btn-primary:hover {
                    background: #fff;
                    transform: translateY(-2px);
                    box-shadow: 0 12px 40px rgba(255,255,255,0.12);
                }
                .btn-ghost {
                    display: inline-block;
                    padding: 14px 32px;
                    background: transparent;
                    color: rgba(255,255,255,0.45);
                    font-size: 0.9rem;
                    font-weight: 400;
                    letter-spacing: 0.08em;
                    text-decoration: none;
                    border-radius: 8px;
                    border: 1px solid rgba(255,255,255,0.1);
                    transition: all 0.3s ease;
                }
                .btn-ghost:hover {
                    color: rgba(255,255,255,0.8);
                    border-color: rgba(255,255,255,0.2);
                }
                .btn-large {
                    padding: 18px 48px;
                    font-size: 1rem;
                    border-radius: 10px;
                }

                /* ── 스크롤 힌트 ── */
                .hero-scroll-hint {
                    position: absolute;
                    bottom: 36px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 8px;
                    color: rgba(255,255,255,0.18);
                    font-size: 0.7rem;
                    letter-spacing: 0.2em;
                    animation: heroFadeIn 2s ease-out 1s both;
                }
                .scroll-arrow {
                    width: 1px;
                    height: 36px;
                    background: linear-gradient(to bottom, rgba(255,255,255,0.2), transparent);
                    animation: scrollArrow 2s ease-in-out infinite;
                }
                @keyframes scrollArrow {
                    0%, 100% { transform: scaleY(1); opacity: 0.4; }
                    50% { transform: scaleY(0.6); opacity: 0.1; }
                }

                /* ── 통계 ── */
                .stats-section {
                    padding: 64px 40px;
                    max-width: 900px;
                    margin: 0 auto;
                }
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 1px;
                    background: rgba(255,255,255,0.04);
                    border-radius: 16px;
                    overflow: hidden;
                    border: 1px solid rgba(255,255,255,0.06);
                }
                .stat-item {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 8px;
                    padding: 40px 24px;
                    background: rgba(255,255,255,0.015);
                    transition: background 0.3s ease;
                }
                .stat-item:hover { background: rgba(255,255,255,0.035); }
                .stat-value {
                    font-size: clamp(1.8rem, 4vw, 2.8rem);
                    font-weight: 900;
                    color: rgba(255,255,255,0.9);
                    letter-spacing: -0.02em;
                }
                .stat-label {
                    font-size: 0.78rem;
                    font-weight: 300;
                    color: rgba(255,255,255,0.3);
                    letter-spacing: 0.15em;
                }

                /* ── 구분선 ── */
                .section-divider {
                    width: 100%;
                    max-width: 900px;
                    margin: 0 auto;
                    height: 1px;
                    background: linear-gradient(
                        90deg,
                        transparent,
                        rgba(255,255,255,0.06) 20%,
                        rgba(255,255,255,0.06) 80%,
                        transparent
                    );
                }

                /* ── 섹션 공통 ── */
                .section-header {
                    text-align: center;
                    margin-bottom: 56px;
                }
                .section-eyebrow {
                    font-size: 0.72rem;
                    font-weight: 400;
                    color: rgba(255,255,255,0.3);
                    letter-spacing: 0.3em;
                    text-transform: uppercase;
                    margin: 0 0 16px;
                }
                .section-title {
                    font-size: clamp(1.6rem, 4vw, 2.4rem);
                    font-weight: 800;
                    color: rgba(255,255,255,0.88);
                    line-height: 1.3;
                    margin: 0;
                    letter-spacing: -0.01em;
                }

                /* ── 기능 카드 ── */
                .features-section {
                    padding: 80px 40px;
                    max-width: 960px;
                    margin: 0 auto;
                }
                .features-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 16px;
                }
                .feature-card {
                    padding: 36px 32px;
                    border-radius: 16px;
                    border: 1px solid;
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                    cursor: default;
                }
                .feature-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 16px 48px rgba(0,0,0,0.4);
                }
                .feature-icon {
                    margin-bottom: 16px;
                }
                .feature-label {
                    font-size: 1.05rem;
                    font-weight: 700;
                    margin: 0 0 12px;
                    letter-spacing: 0.02em;
                }
                .feature-desc {
                    font-size: 0.88rem;
                    font-weight: 300;
                    color: rgba(255,255,255,0.5);
                    line-height: 1.7;
                    margin: 0 0 16px;
                    white-space: pre-line;
                }
                .feature-detail {
                    display: inline-block;
                    font-size: 0.72rem;
                    color: rgba(255,255,255,0.2);
                    letter-spacing: 0.1em;
                    border-top: 1px solid rgba(255,255,255,0.06);
                    padding-top: 14px;
                    width: 100%;
                }

                /* ── 이용 방법 ── */
                .how-section {
                    padding: 80px 40px;
                    max-width: 720px;
                    margin: 0 auto;
                }
                .steps-list {
                    display: flex;
                    flex-direction: column;
                    gap: 0;
                }
                .step-item {
                    position: relative;
                    display: flex;
                    align-items: flex-start;
                    gap: 28px;
                    padding: 32px 0;
                }
                .step-connector {
                    position: absolute;
                    left: 20px;
                    top: calc(50% + 20px);
                    bottom: calc(-50% + 20px);
                    width: 1px;
                    background: linear-gradient(to bottom, rgba(255,255,255,0.12), rgba(255,255,255,0.04));
                }
                .step-num {
                    flex-shrink: 0;
                    width: 40px;
                    height: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.72rem;
                    font-weight: 700;
                    color: rgba(255,255,255,0.35);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 50%;
                    letter-spacing: 0.05em;
                    background: rgba(255,255,255,0.02);
                }
                .step-body { flex: 1; }
                .step-title {
                    font-size: 1.1rem;
                    font-weight: 700;
                    color: rgba(255,255,255,0.85);
                    margin: 0 0 8px;
                    letter-spacing: 0.02em;
                }
                .step-desc {
                    font-size: 0.88rem;
                    font-weight: 300;
                    color: rgba(255,255,255,0.4);
                    line-height: 1.7;
                    margin: 0;
                    letter-spacing: 0.01em;
                }

                /* ── CTA ── */
                .cta-section {
                    position: relative;
                    padding: 120px 40px;
                    text-align: center;
                    overflow: hidden;
                }
                .cta-glow {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: 600px;
                    height: 400px;
                    background: radial-gradient(ellipse at center,
                        rgba(255,255,255,0.04) 0%,
                        rgba(255,255,255,0.01) 40%,
                        transparent 70%
                    );
                    pointer-events: none;
                    border-radius: 50%;
                }
                .cta-eyebrow {
                    font-size: 0.72rem;
                    font-weight: 400;
                    color: rgba(255,255,255,0.25);
                    letter-spacing: 0.3em;
                    text-transform: uppercase;
                    margin: 0 0 20px;
                }
                .cta-title {
                    font-size: clamp(1.8rem, 5vw, 3rem);
                    font-weight: 900;
                    color: rgba(255,255,255,0.92);
                    line-height: 1.2;
                    margin: 0 0 48px;
                    letter-spacing: -0.01em;
                }
                .cta-note {
                    margin: 20px 0 0;
                    font-size: 0.78rem;
                    color: rgba(255,255,255,0.2);
                    letter-spacing: 0.05em;
                }

                /* ── 푸터 ── */
                .about-footer {
                    padding: 48px 40px;
                    border-top: 1px solid rgba(255,255,255,0.04);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 12px;
                }
                .footer-logo {
                    font-size: 1rem;
                    font-weight: 900;
                    color: rgba(255,255,255,0.3);
                    text-decoration: none;
                    letter-spacing: 0.1em;
                }
                .footer-copy {
                    font-size: 0.75rem;
                    color: rgba(255,255,255,0.15);
                    letter-spacing: 0.15em;
                    margin: 0;
                }

                /* ── 반응형 ── */
                @media (max-width: 768px) {
                    .top-nav { padding: 16px 20px; }
                    .hero-section { padding: 100px 20px 60px; }
                    .stats-section { padding: 48px 20px; }
                    .stats-grid { grid-template-columns: repeat(2, 1fr); }
                    .features-section { padding: 60px 20px; }
                    .features-grid { grid-template-columns: 1fr; }
                    .how-section { padding: 60px 20px; }
                    .cta-section { padding: 80px 20px; }
                    .about-footer { padding: 36px 20px; }
                    .feature-card { padding: 28px 24px; }
                }

                @media (max-width: 480px) {
                    .hero-actions { flex-direction: column; align-items: center; }
                    .btn-primary, .btn-ghost { width: min(280px, 90vw); text-align: center; }
                    .stats-grid { grid-template-columns: repeat(2, 1fr); }
                    .stat-item { padding: 28px 16px; }
                }
            `}</style>
        </div>
    );
}
