"use client";

import { useEffect, useRef, useState } from "react";

/* ─── 스크롤 인뷰 훅 ─── */
function useInView(threshold = 0.12) {
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

/* ─── 섹션 래퍼 ─── */
function FadeSection({ children, className = "", delay = 0 }: {
    children: React.ReactNode; className?: string; delay?: number;
}) {
    const { ref, visible } = useInView();
    return (
        <div
            ref={ref}
            className={className}
            style={{
                opacity: visible ? 1 : 0,
                transform: visible ? "translateY(0)" : "translateY(28px)",
                transition: `opacity 0.7s ease ${delay}s, transform 0.7s ease ${delay}s`,
            }}
        >
            {children}
        </div>
    );
}

/* ─── 기능 태그 ─── */
function Tag({ label, accent }: { label: string; accent: string }) {
    return (
        <span style={{
            display: "inline-block",
            padding: "3px 10px",
            borderRadius: "20px",
            fontSize: "0.72rem",
            fontWeight: 500,
            color: accent,
            background: `${accent.replace(")", ", 0.08)").replace("rgba(", "rgba(")}`,
            border: `1px solid ${accent.replace(")", ", 0.2)").replace("rgba(", "rgba(")}`,
            letterSpacing: "0.04em",
        }}>
            {label}
        </span>
    );
}

export default function AboutPage() {
    const heroRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleScroll = () => {
            if (heroRef.current) {
                heroRef.current.style.transform = `translateY(${window.scrollY * 0.25}px)`;
            }
        };
        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    return (
        <div className="wrap">
            {/* ── 상단 내비게이션 ── */}
            <nav className="top-nav">
                <a href="/" className="nav-logo">공잘알</a>
                <div className="nav-right">
                    <a href="/chat" className="nav-ghost">무료 체험</a>
                    <a href="/login" className="nav-cta">시작하기 →</a>
                </div>
            </nav>

            {/* ═══════════════════════════════════════
                HERO
            ═══════════════════════════════════════ */}
            <section className="hero">
                <div className="hero-bg" ref={heroRef}>
                    {[...Array(8)].map((_, i) => (
                        <div key={i} className="orb" style={{
                            left: `${8 + i * 12}%`,
                            width: `${160 + i * 35}px`,
                            height: `${160 + i * 35}px`,
                            animationDelay: `${i * 1.1}s`,
                        }} />
                    ))}
                </div>
                <div className="hero-body">
                    <p className="eyebrow">공무원 시험 AI 플랫폼</p>
                    <h1 className="hero-title">
                        수험생의 합격률을<br />
                        <span className="accent-text">높이기 위한 AI,</span><br />
                        공잘알
                    </h1>
                    <p className="hero-sub">
                        2년간 공시를 준비했던 개발자가 직접 기획한<br />
                        실제 합격자 4,910명의 데이터 기반 맞춤형 공시 AI
                    </p>
                    <div className="hero-btns">
                        <a href="/login" className="btn-white">무료로 시작하기</a>
                        <a href="/chat" className="btn-outline">게스트로 체험하기</a>
                    </div>
                </div>
                <div className="scroll-hint">
                    <span>스크롤</span>
                    <div className="scroll-line" />
                </div>
            </section>

            {/* ═══════════════════════════════════════
                기획 의도
            ═══════════════════════════════════════ */}
            <section className="section section-story">
                <FadeSection className="story-inner">
                    <p className="section-eyebrow">기획 의도</p>
                    <h2 className="section-title">"2년간 공시를 준비하며<br />느꼈던 것들을 담았습니다"</h2>
                    <div className="story-grid">
                        <div className="story-text">
                            <p>
                                공잘알은 직접 2년간 공무원 시험을 준비했던 개발자가 만들었습니다.
                                수험 기간 동안 <strong>"어떤 교재를 써야 하지?", "학원을 다녀야 할까?",
                                    "이 방식이 맞는 건지..."</strong> 라는 불안감은 끊이지 않았습니다.
                            </p>
                            <p>
                                정보는 넘쳐나지만 나에게 딱 맞는 정보는 없었습니다.
                                합격자 카페 글들은 제각각이고, 유료 컨설팅은 접근이 어려웠습니다.
                            </p>
                            <p>
                                그래서 생각했습니다. <em>"수천 명의 합격자 데이터를 AI로 분석해서
                                    나와 가장 비슷한 상황의 합격자가 어떻게 했는지 알려줄 수 있다면?"</em>
                            </p>
                            <p>
                                공잘알은 수험생들이 시험에만 온전히 집중할 수 있도록,
                                불필요한 고민을 줄여주기 위해 만들어졌습니다.
                            </p>
                        </div>
                        <div className="story-cards">
                            {[
                                { q: "어떤 교재가 나에게 맞을까?", a: "합격자 데이터로 답합니다" },
                                { q: "학원 vs 독학, 어떻게 결정하지?", a: "수천 명의 선택을 분석했습니다" },
                                { q: "체력 관리도 시험 준비에 포함될까?", a: "합격자 실데이터로 확인하세요" },
                                { q: "나는 몇 달이면 합격할 수 있을까?", a: "AI가 유사 합격자를 매칭합니다" },
                            ].map((item, i) => (
                                <FadeSection key={i} delay={i * 0.08}>
                                    <div className="story-card">
                                        <p className="story-q">{item.q}</p>
                                        <p className="story-a">{item.a}</p>
                                    </div>
                                </FadeSection>
                            ))}
                        </div>
                    </div>
                </FadeSection>
            </section>

            {/* ═══════════════════════════════════════
                통계
            ═══════════════════════════════════════ */}
            <FadeSection className="stats-wrap">
                <div className="stats-row">
                    {[
                        { val: "4,910", sub: "건", label: "실제 합격 수기 데이터" },
                        { val: "4", sub: "가지", label: "핵심 학습 도구" },
                        { val: "24/7", sub: "", label: "언제나 이용 가능" },
                        { val: "무료", sub: "", label: "베타 서비스 전면 무료" },
                    ].map((s, i) => (
                        <div key={i} className="stat-cell">
                            <div className="stat-val">{s.val}<span className="stat-sub">{s.sub}</span></div>
                            <div className="stat-label">{s.label}</div>
                        </div>
                    ))}
                </div>
            </FadeSection>

            <div className="divider-line" />

            {/* ═══════════════════════════════════════
                FEATURE 1 — AI 챗봇
            ═══════════════════════════════════════ */}
            <section className="section feat-section">
                <FadeSection>
                    <div className="feat-header">
                        <span className="feat-num indigo-text">01</span>
                        <p className="section-eyebrow">AI 멘토 챗봇</p>
                    </div>
                    <h2 className="section-title">
                        공시에 관한 모든 질문,<br />
                        <span className="indigo-text">합격자 데이터로 답합니다</span>
                    </h2>
                    <p className="feat-desc">
                        GPT·Gemini처럼 대화하되, 오직 공무원 시험에 최적화된 AI입니다.
                        공시와 무관한 질문은 자동으로 차단하여 수험생이 학습에만 집중할 수 있도록 합니다.
                    </p>
                </FadeSection>

                <div className="feat-grid-2">
                    {[
                        {
                            icon: "💬",
                            title: "합격자 수기 기반 맞춤 조언",
                            desc: "단순 정보 제공이 아니라, 실제 합격자 4,910명이 어떻게 했는지를 AI가 분석해 답합니다. 교재 추천, 학원 vs 독학 판단, 과목별 공부법, 체력 관리 팁까지 방대한 실데이터를 근거로 제공합니다.",
                            tags: ["교재 추천", "공부법", "학원 vs 독학", "체력관리"],
                            accent: "rgba(99,102,241,1)",
                        },
                        {
                            icon: "🔍",
                            title: "시험 정답 조회",
                            desc: "최신 공무원 시험 정답을 채팅창에서 바로 조회할 수 있습니다. \"9급 행정직 2024년 국어 3번 정답이 뭐야?\"처럼 자연어로 물어보면 즉시 답변합니다.",
                            tags: ["시험 정답", "과목별 조회", "최신 시험"],
                            accent: "rgba(99,102,241,1)",
                        },
                        {
                            icon: "📅",
                            title: "학습 계획 채팅 조회",
                            desc: "\"내 학습계획 보여줘\"라고 채팅하면 AI가 생성한 나만의 학습 계획을 채팅창에서 바로 확인할 수 있습니다. 학습 분석 페이지로 이동하지 않아도 됩니다.",
                            tags: ["학습계획 조회", "AI 플랜"],
                            accent: "rgba(99,102,241,1)",
                        },
                        {
                            icon: "🚫",
                            title: "도메인 외 질문 자동 차단",
                            desc: "공무원 시험과 무관한 질문은 AI가 자동으로 차단합니다. 수험 기간 중 불필요한 정보에 시간을 낭비하지 않도록, 오로지 합격에 필요한 정보만 제공합니다.",
                            tags: ["스마트 차단", "집중 지원"],
                            accent: "rgba(99,102,241,1)",
                        },
                    ].map((item, i) => (
                        <FadeSection key={i} delay={i * 0.1}>
                            <div className="feat-card indigo-card">
                                <div className="feat-card-icon">{item.icon}</div>
                                <h3 className="feat-card-title">{item.title}</h3>
                                <p className="feat-card-desc">{item.desc}</p>
                                <div className="tag-row">
                                    {item.tags.map((t, j) => (
                                        <Tag key={j} label={t} accent={item.accent} />
                                    ))}
                                </div>
                            </div>
                        </FadeSection>
                    ))}
                </div>

                {/* 예시 질문 리스트 */}
                <FadeSection>
                    <div className="example-box indigo-border">
                        <p className="example-label">💡 이런 것들을 물어볼 수 있어요</p>
                        <div className="example-chips">
                            {[
                                "노베이스로 1년 만에 9급 일행직 합격 가능해?",
                                "행정법 교재 뭐가 좋아?",
                                "단기합격자들은 독학 많이 해?",
                                "시험 준비 중 체력 관리 어떻게 해?",
                                "9급 2024 국어 3번 정답이 뭐야?",
                                "내 학습계획 보여줘",
                                "국가직 vs 지방직 어떤게 유리해?",
                                "합격자들이 하루 몇 시간 공부했어?",
                            ].map((q, i) => (
                                <span key={i} className="chip indigo-chip">"{q}"</span>
                            ))}
                        </div>
                    </div>
                </FadeSection>
            </section>

            <div className="divider-line" />

            {/* ═══════════════════════════════════════
                FEATURE 2 — 가상 모의고사
            ═══════════════════════════════════════ */}
            <section className="section feat-section">
                <FadeSection>
                    <div className="feat-header">
                        <span className="feat-num green-text">02</span>
                        <p className="section-eyebrow">가상 모의고사</p>
                    </div>
                    <h2 className="section-title">
                        실전처럼 풀고,<br />
                        <span className="green-text">AI가 완전히 분석합니다</span>
                    </h2>
                    <p className="feat-desc">
                        단순한 문제 풀이를 넘어, 풀이 기록이 곧 AI 학습 분석의 핵심 데이터가 됩니다.
                        많이 풀수록 AI의 분석 정확도가 높아집니다.
                    </p>
                </FadeSection>

                {/* 두 가지 모드 비교 */}
                <FadeSection>
                    <div className="compare-box">
                        <div className="compare-head">
                            <h3 className="compare-title">두 가지 풀기 방식</h3>
                        </div>
                        <div className="compare-grid">
                            <div className="compare-card green-card">
                                <div className="compare-badge">랜덤으로 풀기</div>
                                <p className="compare-sub">실전 감각 유지에 최적</p>
                                <ul className="compare-list">
                                    <li>출제 범위 전체에서 문제를 무작위로 선별</li>
                                    <li>예측 불가한 문제 순서로 실제 시험 환경과 동일</li>
                                    <li>자주 틀리는 유형이 자동으로 더 많이 출제</li>
                                    <li>취약점을 자연스럽게 집중 보완</li>
                                    <li>시험 직전 전범위 점검에 적합</li>
                                </ul>
                                <div className="compare-tag-row">
                                    <Tag label="전범위" accent="rgba(52,211,153,1)" />
                                    <Tag label="실전형" accent="rgba(52,211,153,1)" />
                                    <Tag label="자동 취약점 보완" accent="rgba(52,211,153,1)" />
                                </div>
                            </div>
                            <div className="compare-card green-card-dim">
                                <div className="compare-badge compare-badge-dim">선택해서 풀기</div>
                                <p className="compare-sub">집중 학습에 최적</p>
                                <ul className="compare-list">
                                    <li>시험 연도, 과목, 유형을 직접 선택</li>
                                    <li>특정 과목·단원만 집중 반복 가능</li>
                                    <li>약점 과목을 중점적으로 파고들 때 활용</li>
                                    <li>특정 시험 년도의 문제만 풀기 가능</li>
                                    <li>시험 초반 기초 다지기에 적합</li>
                                </ul>
                                <div className="compare-tag-row">
                                    <Tag label="과목 선택" accent="rgba(52,211,153,0.6)" />
                                    <Tag label="연도 선택" accent="rgba(52,211,153,0.6)" />
                                    <Tag label="집중 학습형" accent="rgba(52,211,153,0.6)" />
                                </div>
                            </div>
                        </div>
                    </div>
                </FadeSection>

                {/* 시험 후 리뷰 기능 */}
                <FadeSection>
                    <div className="review-box">
                        <p className="section-eyebrow" style={{ marginBottom: "16px" }}>시험 후 리뷰 기능</p>
                        <h3 className="review-title">풀고 끝이 아닙니다 — 리뷰가 진짜 공부입니다</h3>
                        <div className="review-grid">
                            {[
                                {
                                    icon: "📋",
                                    title: "풀이 기록 열람",
                                    desc: "내가 선택한 답, 소요 시간, 정답 여부를 문항별로 한눈에 확인합니다.",
                                },
                                {
                                    icon: "💡",
                                    title: "오답 해설 제공",
                                    desc: "틀린 문제에 대한 상세 해설을 즉시 확인합니다. 왜 틀렸는지 정확히 파악할 수 있습니다.",
                                },
                                {
                                    icon: "🔊",
                                    title: "TTS 해설 듣기",
                                    desc: "해설을 텍스트로 읽는 것을 넘어, 음성(TTS)으로 들을 수 있습니다. 이동 중이나 피로할 때도 학습을 이어갈 수 있습니다.",
                                },
                                {
                                    icon: "💾",
                                    title: "풀이 기록 저장",
                                    desc: "오답 노트를 파일로 저장할 수 있습니다. 취약 문제를 별도 관리하거나 출력해 반복 학습에 활용하세요.",
                                },
                            ].map((item, i) => (
                                <div key={i} className="review-card">
                                    <span className="review-icon">{item.icon}</span>
                                    <h4 className="review-card-title">{item.title}</h4>
                                    <p className="review-card-desc">{item.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </FadeSection>
            </section>

            <div className="divider-line" />

            {/* ═══════════════════════════════════════
                FEATURE 3 — 학습 분석 & AI 플랜
            ═══════════════════════════════════════ */}
            <section className="section feat-section">
                <FadeSection>
                    <div className="feat-header">
                        <span className="feat-num yellow-text">03</span>
                        <p className="section-eyebrow">학습 분석 & AI 플랜</p>
                    </div>
                    <h2 className="section-title">
                        나와 가장 닮은 합격자를<br />
                        <span className="yellow-text">AI가 찾아드립니다</span>
                    </h2>
                    <p className="feat-desc">
                        단순한 학습 계획 생성이 아닙니다.
                        내 정보와 모의고사 풀이 기록을 종합적으로 분석해
                        가장 유사한 실제 합격자 수기를 매칭하고, 그 합격자의 경험을 AI가 요약해 제공합니다.
                    </p>
                </FadeSection>

                {/* 3단계 AI 플랜 프로세스 */}
                <FadeSection>
                    <div className="process-box">
                        <h3 className="process-title">AI 플랜이 만들어지는 과정</h3>
                        <div className="process-steps">
                            {[
                                {
                                    num: "1",
                                    title: "학습 프로필 입력",
                                    desc: "사용자 정보 페이지에서 나의 현재 상황을 입력합니다.",
                                    items: ["나이", "직장 재직 여부", "공시 초시 여부", "목표 합격 기간", "목표 직렬", "강점 과목", "취약 과목"],
                                    accent: "rgba(251,191,36,1)",
                                },
                                {
                                    num: "2",
                                    title: "가상 모의고사 풀이",
                                    desc: "모의고사를 풀면 AI가 풀이 데이터를 자동 수집·분석합니다.",
                                    items: ["과목별 정답률", "풀이 소요 시간", "자주 틀리는 유형", "약점 단원 파악", "시간 관리 패턴"],
                                    accent: "rgba(251,191,36,1)",
                                },
                                {
                                    num: "3",
                                    title: "유사 합격자 매칭",
                                    desc: "프로필 + 풀이 분석을 종합해 가장 유사한 합격자를 찾습니다.",
                                    items: ["4,910건의 수기에서 매칭", "나이·직장·초시 여부 반영", "목표 직렬 유사도 분석", "합격 기간 유사도 반영"],
                                    accent: "rgba(251,191,36,1)",
                                },
                                {
                                    num: "4",
                                    title: "AI 학습 계획 생성",
                                    desc: "매칭된 합격자 수기 원본을 AI가 나에게 맞게 요약·정리합니다.",
                                    items: ["합격자 수기 원본 AI 요약", "단계별 커리큘럼 구성", "과목별 학습 비중 제안", "주간·월간 학습 일정"],
                                    accent: "rgba(251,191,36,1)",
                                },
                            ].map((step, i) => (
                                <FadeSection key={i} delay={i * 0.1}>
                                    <div className="process-step">
                                        <div className="process-num yellow-text">{step.num}</div>
                                        <div className="process-body">
                                            <h4 className="process-step-title">{step.title}</h4>
                                            <p className="process-step-desc">{step.desc}</p>
                                            <div className="process-items">
                                                {step.items.map((it, j) => (
                                                    <span key={j} className="process-item yellow-item">{it}</span>
                                                ))}
                                            </div>
                                        </div>
                                        {i < 3 && <div className="process-arrow">↓</div>}
                                    </div>
                                </FadeSection>
                            ))}
                        </div>
                    </div>
                </FadeSection>

                {/* 학습 프로필 상세 */}
                <FadeSection>
                    <div className="profile-box">
                        <p className="section-eyebrow" style={{ marginBottom: "12px" }}>학습 프로필</p>
                        <h3 className="profile-title">정확할수록, 더 나에게 맞는 결과가 나옵니다</h3>
                        <div className="profile-grid">
                            {[
                                { label: "나이", icon: "👤", desc: "연령대별 합격자 데이터를 매칭에 반영합니다" },
                                { label: "직장 재직 여부", icon: "💼", desc: "직장인 vs 전업 수험생 합격 전략이 다릅니다" },
                                { label: "초시 여부", icon: "🎯", desc: "처음 도전인지, 재도전인지에 따라 전략이 달라집니다" },
                                { label: "목표 합격 기간", icon: "📆", desc: "6개월·1년·2년 등 목표 기간에 맞는 커리큘럼을 구성합니다" },
                                { label: "목표 직렬", icon: "🏛", desc: "9급 일반행정직, 세무직, 기술직 등 직렬별 전략이 다릅니다" },
                                { label: "강점 / 취약 과목", icon: "📊", desc: "강점은 유지하고, 취약 과목에 집중할 수 있도록 비중을 조정합니다" },
                            ].map((p, i) => (
                                <div key={i} className="profile-card">
                                    <span className="profile-icon">{p.icon}</span>
                                    <h4 className="profile-label">{p.label}</h4>
                                    <p className="profile-card-desc">{p.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </FadeSection>
            </section>

            <div className="divider-line" />

            {/* ═══════════════════════════════════════
                FEATURE 4 — 자료 업로드
            ═══════════════════════════════════════ */}
            <section className="section feat-section">
                <FadeSection>
                    <div className="feat-header">
                        <span className="feat-num pink-text">04</span>
                        <p className="section-eyebrow">자료 업로드</p>
                    </div>
                    <h2 className="section-title">
                        시험 자료를 업로드하면<br />
                        <span className="pink-text">AI가 자동으로 분석합니다</span>
                    </h2>
                    <p className="feat-desc">
                        해설지, 문제지를 업로드하면 AI가 자동으로 분류·분석해 데이터베이스에 추가합니다.
                        수험생들이 자료를 공유함으로써 AI의 지식이 함께 성장합니다.
                    </p>
                </FadeSection>
                <div className="feat-grid-3">
                    {[
                        { icon: "📄", title: "해설지 업로드", desc: "해설 자료를 업로드하면 AI가 핵심 내용을 추출해 데이터베이스에 저장합니다." },
                        { icon: "📝", title: "문제지 업로드", desc: "기출문제 이미지나 PDF를 업로드하면 AI가 자동으로 문항을 분류하고 등록합니다." },
                        { icon: "🤖", title: "AI 자동 분류", desc: "업로드된 자료는 AI가 과목·연도·유형을 자동 판단해 분류하므로 별도 태깅이 필요 없습니다." },
                    ].map((item, i) => (
                        <FadeSection key={i} delay={i * 0.1}>
                            <div className="feat-card pink-card">
                                <span className="feat-card-icon">{item.icon}</span>
                                <h3 className="feat-card-title">{item.title}</h3>
                                <p className="feat-card-desc">{item.desc}</p>
                            </div>
                        </FadeSection>
                    ))}
                </div>
            </section>

            <div className="divider-line" />

            {/* ═══════════════════════════════════════
                데이터 품질
            ═══════════════════════════════════════ */}
            <section className="section">
                <FadeSection>
                    <div className="quality-box">
                        <p className="section-eyebrow">데이터 품질</p>
                        <h2 className="section-title">왜 공잘알의 답변은<br />다를 수밖에 없을까요</h2>
                        <div className="quality-grid">
                            {[
                                {
                                    icon: "📊",
                                    title: "4,910건의 실제 합격 수기",
                                    desc: "인터넷에 떠도는 정보가 아닌, 실제 합격자들이 직접 작성한 수기 데이터를 기반으로 합니다. 가공되지 않은 날것의 경험담에서 진짜 인사이트를 추출합니다.",
                                },
                                {
                                    icon: "🎯",
                                    title: "합격자 매칭 알고리즘",
                                    desc: "\"일반적인 9급 합격법\"이 아닌, 나와 가장 유사한 조건(나이, 직장, 목표 직렬, 초시 여부)의 합격자를 매칭해 그 사람의 공부법을 알려드립니다.",
                                },
                                {
                                    icon: "🔒",
                                    title: "도메인 특화 AI",
                                    desc: "공시와 무관한 내용은 AI가 응답하지 않습니다. 오직 공무원 시험에 필요한 정보만 정제해서 전달하기 때문에 정보의 품질과 신뢰도가 보장됩니다.",
                                },
                            ].map((item, i) => (
                                <FadeSection key={i} delay={i * 0.1}>
                                    <div className="quality-card">
                                        <span className="quality-icon">{item.icon}</span>
                                        <h3 className="quality-title">{item.title}</h3>
                                        <p className="quality-desc">{item.desc}</p>
                                    </div>
                                </FadeSection>
                            ))}
                        </div>
                    </div>
                </FadeSection>
            </section>

            <div className="divider-line" />

            {/* ═══════════════════════════════════════
                이용 방법
            ═══════════════════════════════════════ */}
            <section className="section">
                <FadeSection>
                    <p className="section-eyebrow" style={{ textAlign: "center" }}>이용 방법</p>
                    <h2 className="section-title" style={{ textAlign: "center" }}>지금 바로 시작할 수 있습니다</h2>
                </FadeSection>
                <div className="start-steps">
                    {[
                        {
                            num: "01",
                            title: "소셜 로그인 (3초)",
                            desc: "카카오, 네이버, 구글 중 편한 계정으로 로그인하세요. 별도 회원가입 없이 즉시 이용 가능합니다.",
                            action: "→ /login",
                        },
                        {
                            num: "02",
                            title: "학습 프로필 입력",
                            desc: "사용자 정보 페이지에서 나이, 목표 직렬, 취약 과목 등을 입력합니다. 더 정확한 AI 매칭을 위한 핵심 단계입니다.",
                            action: "→ /user",
                        },
                        {
                            num: "03",
                            title: "AI 챗봇으로 질문",
                            desc: "궁금한 것은 무엇이든 챗봇에 물어보세요. 교재 추천, 공부법, 시험 정답까지 바로 답변합니다.",
                            action: "→ /chat",
                        },
                        {
                            num: "04",
                            title: "모의고사 풀기",
                            desc: "랜덤 또는 선택 방식으로 모의고사를 풀고, 풀이 후 TTS 해설과 오답 분석으로 약점을 보완합니다.",
                            action: "→ /test_exam",
                        },
                        {
                            num: "05",
                            title: "AI 학습 계획 받기",
                            desc: "풀이 기록이 쌓이면 AI가 유사 합격자를 매칭하고, 나에게 최적화된 학습 계획을 생성해줍니다.",
                            action: "→ /study-plan",
                        },
                    ].map((step, i) => (
                        <FadeSection key={i} delay={i * 0.08}>
                            <div className="start-step">
                                <div className="start-step-left">
                                    <span className="start-num">{step.num}</span>
                                    {i < 4 && <div className="start-connector" />}
                                </div>
                                <div className="start-body">
                                    <h3 className="start-title">{step.title}</h3>
                                    <p className="start-desc">{step.desc}</p>
                                    <span className="start-action">{step.action}</span>
                                </div>
                            </div>
                        </FadeSection>
                    ))}
                </div>
            </section>

            {/* ═══════════════════════════════════════
                CTA
            ═══════════════════════════════════════ */}
            <FadeSection className="cta-wrap">
                <div className="cta-glow" />
                <p className="section-eyebrow">지금 바로</p>
                <h2 className="cta-title">
                    합격의 첫 걸음을<br />공잘알과 함께 시작하세요
                </h2>
                <p className="cta-sub">별도 설치 없이 브라우저에서 바로 이용 가능합니다</p>
                <div className="hero-btns" style={{ marginTop: "40px" }}>
                    <a href="/login" className="btn-white btn-large">무료로 시작하기</a>
                    <a href="/chat" className="btn-outline">게스트로 체험하기</a>
                </div>
            </FadeSection>

            {/* ═══════════════════════════════════════
                FOOTER
            ═══════════════════════════════════════ */}
            <footer className="footer">
                <a href="/" className="footer-logo">공잘알</a>
                <p className="footer-copy">공무원 시험, 잘 알려주는 AI</p>
            </footer>

            {/* ═══════════════════════════════════════
                STYLES
            ═══════════════════════════════════════ */}
            <style jsx>{`
                * { box-sizing: border-box; }

                .wrap {
                    min-height: 100vh;
                    background: #000;
                    color: #fff;
                    font-family: "Gothic A1","Noto Sans KR","Malgun Gothic",sans-serif;
                    overflow-x: hidden;
                }

                /* ── 내비 ── */
                .top-nav {
                    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
                    display: flex; align-items: center; justify-content: space-between;
                    padding: 18px 40px;
                    background: rgba(0,0,0,0.7);
                    backdrop-filter: blur(16px);
                    border-bottom: 1px solid rgba(255,255,255,0.04);
                }
                .nav-logo {
                    font-size: 1.15rem; font-weight: 900; color: #fff;
                    text-decoration: none; letter-spacing: 0.05em;
                }
                .nav-right { display: flex; align-items: center; gap: 20px; }
                .nav-ghost {
                    font-size: 0.8rem; color: rgba(255,255,255,0.35);
                    text-decoration: none; letter-spacing: 0.08em;
                    transition: color 0.3s;
                }
                .nav-ghost:hover { color: rgba(255,255,255,0.7); }
                .nav-cta {
                    font-size: 0.8rem; color: rgba(255,255,255,0.55);
                    text-decoration: none; letter-spacing: 0.1em; transition: color 0.3s;
                }
                .nav-cta:hover { color: #fff; }

                /* ── 히어로 ── */
                .hero {
                    position: relative; min-height: 100vh;
                    display: flex; flex-direction: column;
                    align-items: center; justify-content: center;
                    overflow: hidden; padding: 120px 24px 80px; text-align: center;
                }
                .hero-bg {
                    position: absolute; inset: 0; pointer-events: none;
                }
                .orb {
                    position: absolute; top: 50%; border-radius: 50%;
                    background: radial-gradient(ellipse, rgba(255,255,255,0.022) 0%, transparent 70%);
                    transform: translateY(-50%);
                    animation: orbPulse 9s ease-in-out infinite;
                }
                @keyframes orbPulse {
                    0%,100% { opacity:0.3; transform:translateY(-50%) scale(1); }
                    50% { opacity:0.7; transform:translateY(-50%) scale(1.07); }
                }
                .hero-body {
                    position: relative; z-index: 1; max-width: 720px;
                    animation: fadeUp 1.2s ease-out both;
                }
                @keyframes fadeUp {
                    from { opacity:0; transform:translateY(28px); }
                    to { opacity:1; transform:translateY(0); }
                }
                .eyebrow {
                    font-size: 0.75rem; font-weight: 400;
                    color: rgba(255,255,255,0.3);
                    letter-spacing: 0.35em; text-transform: uppercase;
                    margin: 0 0 24px;
                }
                .hero-title {
                    font-size: clamp(2.2rem, 6vw, 4.2rem);
                    font-weight: 900; line-height: 1.18;
                    margin: 0 0 24px; letter-spacing: -0.02em;
                    color: rgba(255,255,255,0.92);
                }
                .accent-text {
                    color: #fff;
                    text-shadow: 0 0 30px rgba(255,255,255,0.25);
                }
                .hero-sub {
                    font-size: clamp(0.9rem,2vw,1.05rem); font-weight: 300;
                    color: rgba(255,255,255,0.38); line-height: 1.85;
                    margin: 0 0 48px; letter-spacing: 0.02em;
                }
                .hero-btns {
                    display: flex; gap: 14px; justify-content: center; flex-wrap: wrap;
                }
                .btn-white {
                    display: inline-block; padding: 14px 32px;
                    background: rgba(255,255,255,0.94); color: #000;
                    font-size: 0.88rem; font-weight: 700; letter-spacing: 0.08em;
                    text-decoration: none; border-radius: 8px;
                    transition: all 0.3s ease;
                }
                .btn-white:hover {
                    background: #fff; transform: translateY(-2px);
                    box-shadow: 0 12px 40px rgba(255,255,255,0.12);
                }
                .btn-white.btn-large { padding: 17px 48px; font-size: 0.95rem; border-radius: 10px; }
                .btn-outline {
                    display: inline-block; padding: 14px 32px;
                    background: transparent; color: rgba(255,255,255,0.42);
                    font-size: 0.88rem; font-weight: 400; letter-spacing: 0.08em;
                    text-decoration: none; border-radius: 8px;
                    border: 1px solid rgba(255,255,255,0.1);
                    transition: all 0.3s ease;
                }
                .btn-outline:hover { color: rgba(255,255,255,0.8); border-color: rgba(255,255,255,0.2); }
                .scroll-hint {
                    position: absolute; bottom: 32px;
                    display: flex; flex-direction: column; align-items: center; gap: 8px;
                    color: rgba(255,255,255,0.15); font-size: 0.65rem; letter-spacing: 0.2em;
                }
                .scroll-line {
                    width: 1px; height: 32px;
                    background: linear-gradient(to bottom, rgba(255,255,255,0.18), transparent);
                    animation: sAnim 2s ease-in-out infinite;
                }
                @keyframes sAnim { 0%,100%{opacity:0.4;} 50%{opacity:0.1;} }

                /* ── 섹션 공통 ── */
                .section { padding: 80px 40px; max-width: 1080px; margin: 0 auto; }
                .section-eyebrow {
                    font-size: 0.72rem; font-weight: 400;
                    color: rgba(255,255,255,0.28);
                    letter-spacing: 0.32em; text-transform: uppercase; margin: 0 0 14px;
                }
                .section-title {
                    font-size: clamp(1.7rem,4vw,2.6rem); font-weight: 800;
                    color: rgba(255,255,255,0.88); line-height: 1.28; margin: 0 0 20px;
                    letter-spacing: -0.01em;
                }
                .divider-line {
                    width: 100%; max-width: 1080px; margin: 0 auto; height: 1px;
                    background: linear-gradient(90deg,transparent,rgba(255,255,255,0.055) 20%,rgba(255,255,255,0.055) 80%,transparent);
                }

                /* ── 기획 의도 ── */
                .section-story { padding: 80px 40px; max-width: 1080px; margin: 0 auto; }
                .story-inner {}
                .story-grid {
                    display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 40px;
                }
                .story-text p {
                    font-size: 0.92rem; font-weight: 300;
                    color: rgba(255,255,255,0.48); line-height: 1.9; margin: 0 0 18px;
                    letter-spacing: 0.01em;
                }
                .story-text strong { color: rgba(255,255,255,0.72); font-weight: 600; }
                .story-text em {
                    color: rgba(255,255,255,0.65); font-style: normal;
                    border-left: 2px solid rgba(255,255,255,0.15);
                    padding-left: 12px; display: block; margin: 4px 0;
                }
                .story-cards { display: flex; flex-direction: column; gap: 12px; }
                .story-card {
                    padding: 20px 24px;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 12px;
                }
                .story-q {
                    font-size: 0.85rem; color: rgba(255,255,255,0.55);
                    margin: 0 0 8px; font-weight: 400; letter-spacing: 0.01em;
                }
                .story-a {
                    font-size: 0.82rem; color: rgba(255,255,255,0.25);
                    margin: 0; font-weight: 300; letter-spacing: 0.05em;
                }

                /* ── 통계 ── */
                .stats-wrap {
                    padding: 48px 40px; max-width: 1080px; margin: 0 auto;
                }
                .stats-row {
                    display: grid; grid-template-columns: repeat(4,1fr);
                    gap: 1px; background: rgba(255,255,255,0.04);
                    border-radius: 16px; overflow: hidden;
                    border: 1px solid rgba(255,255,255,0.06);
                }
                .stat-cell {
                    display: flex; flex-direction: column; align-items: center; gap: 8px;
                    padding: 36px 16px;
                    background: rgba(255,255,255,0.012);
                    transition: background 0.3s;
                }
                .stat-cell:hover { background: rgba(255,255,255,0.03); }
                .stat-val {
                    font-size: clamp(1.8rem,4vw,2.8rem); font-weight: 900;
                    color: rgba(255,255,255,0.88); letter-spacing:-0.02em;
                }
                .stat-sub { font-size: 1rem; font-weight: 400; margin-left: 2px; }
                .stat-label {
                    font-size: 0.76rem; font-weight: 300;
                    color: rgba(255,255,255,0.28); letter-spacing: 0.12em; text-align: center;
                }

                /* ── 기능 섹션 공통 ── */
                .feat-section { padding: 80px 40px; max-width: 1080px; margin: 0 auto; }
                .feat-header { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
                .feat-num { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.2em; opacity: 0.5; }
                .feat-desc {
                    font-size: 0.95rem; font-weight: 300;
                    color: rgba(255,255,255,0.4); line-height: 1.85;
                    margin: 0 0 48px; max-width: 680px; letter-spacing: 0.01em;
                }
                .feat-grid-2 {
                    display: grid; grid-template-columns: repeat(2,1fr); gap: 16px; margin-bottom: 32px;
                }
                .feat-grid-3 {
                    display: grid; grid-template-columns: repeat(3,1fr); gap: 16px;
                }
                .feat-card {
                    padding: 32px 28px; border-radius: 14px; border: 1px solid;
                    transition: transform 0.3s, box-shadow 0.3s;
                }
                .feat-card:hover { transform: translateY(-4px); box-shadow: 0 16px 48px rgba(0,0,0,0.4); }
                .feat-card-icon { font-size: 1.6rem; margin-bottom: 16px; }
                .feat-card-title {
                    font-size: 1rem; font-weight: 700;
                    color: rgba(255,255,255,0.88); margin: 0 0 10px; letter-spacing: 0.02em;
                }
                .feat-card-desc {
                    font-size: 0.85rem; font-weight: 300;
                    color: rgba(255,255,255,0.45); line-height: 1.75; margin: 0 0 16px;
                }
                .tag-row { display: flex; flex-wrap: wrap; gap: 6px; }
                .indigo-card {
                    background: rgba(99,102,241,0.05);
                    border-color: rgba(99,102,241,0.14);
                }
                .pink-card {
                    background: rgba(244,114,182,0.05);
                    border-color: rgba(244,114,182,0.14);
                }
                .indigo-text { color: rgba(165,168,255,0.9); }
                .green-text { color: rgba(52,211,153,0.9); }
                .yellow-text { color: rgba(253,224,71,0.9); }
                .pink-text { color: rgba(244,114,182,0.9); }

                /* ── 예시 질문 박스 ── */
                .example-box {
                    padding: 28px 32px; border-radius: 14px;
                    background: rgba(99,102,241,0.04);
                    border-width: 1px; border-style: solid;
                }
                .indigo-border { border-color: rgba(99,102,241,0.13); }
                .example-label {
                    font-size: 0.8rem; font-weight: 500;
                    color: rgba(165,168,255,0.7); margin: 0 0 16px; letter-spacing: 0.05em;
                }
                .example-chips { display: flex; flex-wrap: wrap; gap: 8px; }
                .chip {
                    display: inline-block; padding: 6px 14px; border-radius: 20px;
                    font-size: 0.78rem; font-weight: 300; letter-spacing: 0.01em;
                }
                .indigo-chip {
                    background: rgba(99,102,241,0.08);
                    color: rgba(165,168,255,0.7);
                    border: 1px solid rgba(99,102,241,0.15);
                }

                /* ── 모의고사 비교 ── */
                .compare-box {
                    padding: 36px 32px; border-radius: 16px;
                    background: rgba(52,211,153,0.03);
                    border: 1px solid rgba(52,211,153,0.1);
                    margin-bottom: 32px;
                }
                .compare-head { margin-bottom: 24px; }
                .compare-title {
                    font-size: 1.1rem; font-weight: 700;
                    color: rgba(255,255,255,0.8); margin: 0;
                }
                .compare-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
                .compare-card {
                    padding: 28px 24px; border-radius: 12px;
                    background: rgba(52,211,153,0.07);
                    border: 1px solid rgba(52,211,153,0.2);
                }
                .compare-card-dim {
                    background: rgba(52,211,153,0.02);
                    border: 1px solid rgba(52,211,153,0.08);
                }
                .compare-badge {
                    display: inline-block; font-size: 0.78rem; font-weight: 700;
                    color: rgba(52,211,153,0.9); letter-spacing: 0.08em;
                    margin-bottom: 8px;
                }
                .compare-badge-dim { color: rgba(52,211,153,0.5); }
                .compare-sub {
                    font-size: 0.75rem; color: rgba(255,255,255,0.25);
                    letter-spacing: 0.08em; margin: 0 0 16px; font-weight: 300;
                }
                .compare-list {
                    list-style: none; padding: 0; margin: 0 0 16px;
                    display: flex; flex-direction: column; gap: 8px;
                }
                .compare-list li {
                    font-size: 0.84rem; font-weight: 300;
                    color: rgba(255,255,255,0.5); line-height: 1.6;
                    padding-left: 14px; position: relative;
                }
                .compare-list li::before {
                    content: "·"; position: absolute; left: 0;
                    color: rgba(52,211,153,0.5);
                }
                .compare-tag-row { display: flex; flex-wrap: wrap; gap: 6px; }

                /* ── 리뷰 기능 ── */
                .review-box {
                    padding: 36px 32px; border-radius: 16px;
                    background: rgba(255,255,255,0.015);
                    border: 1px solid rgba(255,255,255,0.06);
                }
                .review-title {
                    font-size: 1.05rem; font-weight: 700;
                    color: rgba(255,255,255,0.8); margin: 0 0 28px;
                }
                .review-grid {
                    display: grid; grid-template-columns: repeat(2,1fr); gap: 16px;
                }
                .review-card {
                    padding: 24px 22px; border-radius: 12px;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                }
                .review-icon { font-size: 1.4rem; display: block; margin-bottom: 12px; }
                .review-card-title {
                    font-size: 0.92rem; font-weight: 600;
                    color: rgba(255,255,255,0.78); margin: 0 0 8px;
                }
                .review-card-desc {
                    font-size: 0.82rem; font-weight: 300;
                    color: rgba(255,255,255,0.4); line-height: 1.7; margin: 0;
                }

                /* ── AI 플랜 프로세스 ── */
                .process-box {
                    padding: 36px 32px; border-radius: 16px;
                    background: rgba(251,191,36,0.03);
                    border: 1px solid rgba(251,191,36,0.1);
                    margin-bottom: 32px;
                }
                .process-title {
                    font-size: 1.05rem; font-weight: 700;
                    color: rgba(255,255,255,0.8); margin: 0 0 32px;
                }
                .process-steps { display: flex; flex-direction: column; position: relative; }
                .process-step {
                    display: flex; align-items: flex-start; gap: 24px;
                    padding: 24px 0; position: relative;
                }
                .process-num {
                    flex-shrink: 0; width: 36px; height: 36px;
                    display: flex; align-items: center; justify-content: center;
                    font-size: 0.9rem; font-weight: 800;
                    border: 1px solid rgba(251,191,36,0.25);
                    border-radius: 50%;
                    background: rgba(251,191,36,0.06);
                }
                .process-body { flex: 1; }
                .process-step-title {
                    font-size: 0.98rem; font-weight: 700;
                    color: rgba(255,255,255,0.82); margin: 0 0 8px;
                }
                .process-step-desc {
                    font-size: 0.83rem; font-weight: 300;
                    color: rgba(255,255,255,0.4); line-height: 1.7; margin: 0 0 12px;
                }
                .process-items { display: flex; flex-wrap: wrap; gap: 6px; }
                .process-item {
                    display: inline-block; padding: 3px 10px; border-radius: 20px;
                    font-size: 0.72rem; font-weight: 400; letter-spacing: 0.04em;
                }
                .yellow-item {
                    background: rgba(251,191,36,0.08);
                    color: rgba(253,224,71,0.7);
                    border: 1px solid rgba(251,191,36,0.18);
                }
                .process-arrow {
                    position: absolute; left: 18px; bottom: -4px;
                    font-size: 1rem; color: rgba(251,191,36,0.3);
                }

                /* ── 학습 프로필 ── */
                .profile-box {
                    padding: 36px 32px; border-radius: 16px;
                    background: rgba(255,255,255,0.015);
                    border: 1px solid rgba(255,255,255,0.06);
                }
                .profile-title {
                    font-size: 1rem; font-weight: 600;
                    color: rgba(255,255,255,0.7); margin: 0 0 28px;
                }
                .profile-grid {
                    display: grid; grid-template-columns: repeat(3,1fr); gap: 14px;
                }
                .profile-card {
                    padding: 22px 20px; border-radius: 12px;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                }
                .profile-icon { font-size: 1.3rem; display: block; margin-bottom: 10px; }
                .profile-label {
                    font-size: 0.88rem; font-weight: 600;
                    color: rgba(255,255,255,0.72); margin: 0 0 6px;
                }
                .profile-card-desc {
                    font-size: 0.78rem; font-weight: 300;
                    color: rgba(255,255,255,0.35); line-height: 1.65; margin: 0;
                }

                /* ── 데이터 품질 ── */
                .quality-box { padding: 0; }
                .quality-grid {
                    display: grid; grid-template-columns: repeat(3,1fr); gap: 16px; margin-top: 40px;
                }
                .quality-card {
                    padding: 32px 28px; border-radius: 14px;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                    transition: transform 0.3s, box-shadow 0.3s;
                }
                .quality-card:hover { transform: translateY(-4px); box-shadow: 0 16px 40px rgba(0,0,0,0.4); }
                .quality-icon { font-size: 1.5rem; display: block; margin-bottom: 16px; }
                .quality-title {
                    font-size: 0.95rem; font-weight: 700;
                    color: rgba(255,255,255,0.82); margin: 0 0 10px;
                }
                .quality-desc {
                    font-size: 0.82rem; font-weight: 300;
                    color: rgba(255,255,255,0.4); line-height: 1.75; margin: 0;
                }

                /* ── 시작하기 단계 ── */
                .start-steps {
                    max-width: 680px; margin: 40px auto 0;
                    display: flex; flex-direction: column;
                }
                .start-step {
                    display: flex; gap: 24px; padding: 20px 0;
                }
                .start-step-left {
                    display: flex; flex-direction: column; align-items: center;
                }
                .start-num {
                    flex-shrink: 0; width: 40px; height: 40px;
                    display: flex; align-items: center; justify-content: center;
                    font-size: 0.7rem; font-weight: 700;
                    color: rgba(255,255,255,0.3);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 50%;
                    background: rgba(255,255,255,0.02);
                    letter-spacing: 0.05em; flex-shrink: 0;
                }
                .start-connector {
                    flex: 1; width: 1px; min-height: 20px;
                    background: linear-gradient(to bottom, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
                    margin-top: 4px;
                }
                .start-body { flex: 1; padding-bottom: 8px; }
                .start-title {
                    font-size: 0.98rem; font-weight: 700;
                    color: rgba(255,255,255,0.82); margin: 0 0 6px;
                }
                .start-desc {
                    font-size: 0.83rem; font-weight: 300;
                    color: rgba(255,255,255,0.38); line-height: 1.7; margin: 0 0 8px;
                }
                .start-action {
                    font-size: 0.72rem; color: rgba(255,255,255,0.2);
                    letter-spacing: 0.1em;
                }

                /* ── CTA ── */
                .cta-wrap {
                    position: relative; padding: 120px 40px; text-align: center; overflow: hidden;
                }
                .cta-glow {
                    position: absolute; top: 50%; left: 50%;
                    transform: translate(-50%,-50%);
                    width: 700px; height: 400px;
                    background: radial-gradient(ellipse, rgba(255,255,255,0.04) 0%, transparent 70%);
                    border-radius: 50%; pointer-events: none;
                }
                .cta-title {
                    font-size: clamp(1.8rem,5vw,3rem); font-weight: 900;
                    color: rgba(255,255,255,0.9); line-height: 1.25;
                    margin: 0 0 16px; letter-spacing: -0.01em;
                }
                .cta-sub {
                    font-size: 0.82rem; color: rgba(255,255,255,0.22);
                    letter-spacing: 0.05em; margin: 0;
                }

                /* ── 푸터 ── */
                .footer {
                    padding: 48px 40px;
                    border-top: 1px solid rgba(255,255,255,0.04);
                    display: flex; flex-direction: column;
                    align-items: center; gap: 10px;
                }
                .footer-logo {
                    font-size: 0.95rem; font-weight: 900;
                    color: rgba(255,255,255,0.25); text-decoration: none; letter-spacing: 0.1em;
                }
                .footer-copy {
                    font-size: 0.72rem; color: rgba(255,255,255,0.12);
                    letter-spacing: 0.15em; margin: 0;
                }

                /* ── 반응형 ── */
                @media (max-width: 900px) {
                    .story-grid { grid-template-columns: 1fr; gap: 28px; }
                    .feat-grid-2 { grid-template-columns: 1fr; }
                    .feat-grid-3 { grid-template-columns: 1fr; }
                    .compare-grid { grid-template-columns: 1fr; }
                    .review-grid { grid-template-columns: 1fr; }
                    .profile-grid { grid-template-columns: repeat(2,1fr); }
                    .quality-grid { grid-template-columns: 1fr; }
                    .stats-row { grid-template-columns: repeat(2,1fr); }
                }
                @media (max-width: 640px) {
                    .top-nav { padding: 14px 16px; }
                    .section, .feat-section, .section-story { padding: 56px 16px; }
                    .stats-wrap { padding: 36px 16px; }
                    .hero { padding: 90px 16px 60px; }
                    .compare-box, .review-box, .process-box, .profile-box, .example-box { padding: 24px 16px; }
                    .profile-grid { grid-template-columns: 1fr; }
                    .stats-row { grid-template-columns: repeat(2,1fr); }
                    .hero-btns { flex-direction: column; align-items: center; }
                    .btn-white, .btn-outline { width: min(280px,85vw); text-align: center; }
                    .feat-card { padding: 22px 18px; }
                    .cta-wrap { padding: 80px 16px; }
                    .footer { padding: 36px 16px; }
                }
            `}</style>
        </div>
    );
}
