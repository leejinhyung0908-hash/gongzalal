"use client";

import { useMemo, useState } from "react";

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

const YEARS = ["2026", "2025", "2024", "2023", "2022", "2021"];
const SUBJECTS = [
    "교육학개론",
    "국어",
    "영어",
    "정보봉사개론",
    "지방세법",
    "한국사",
    "행정법총론",
    "행정학개론",
    "회계학",
];
const SERIES = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"];

export default function SelectExamPage() {
    const [year, setYear] = useState("2026");
    const [subject, setSubject] = useState("국어");
    const [series, setSeries] = useState("1월");

    const canStart = useMemo(() => !!(year && subject && series), [year, subject, series]);

    const handleStart = () => {
        if (!canStart) return;
        const params = new URLSearchParams({
            mode: "select",
            year,
            subject,
            series,
            count: "20",
        });
        window.location.href = `/test_exam/random?${params.toString()}`;
    };

    return (
        <div className="exam-container">
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

            <a href="/" className="top-logo">
                <span>공</span><span>잘</span><span>알</span>
            </a>

            <div className="content">
                <div className="title-wrap">
                    <p className="kicker">가상 모의고사</p>
                    <h1 className="title">선택해서 풀기</h1>
                    <p className="subtitle">원하는 연도/과목/회차를 선택해 공무원 문제를 풀어보세요.</p>
                </div>

                <div className="layout">
                    <section className="card form-card">
                        <h2 className="section-title">문제 조건 선택</h2>

                        <div className="field">
                            <span className="label">년도</span>
                            <div className="chip-grid">
                                {YEARS.map((item) => (
                                    <button
                                        key={item}
                                        className={`chip ${year === item ? "active" : ""}`}
                                        onClick={() => setYear(item)}
                                    >
                                        {item}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="field">
                            <span className="label">과목</span>
                            <div className="chip-grid wide">
                                {SUBJECTS.map((item) => (
                                    <button
                                        key={item}
                                        className={`chip ${subject === item ? "active" : ""}`}
                                        onClick={() => setSubject(item)}
                                    >
                                        {item}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="field">
                            <span className="label">회차</span>
                            <select value={series} onChange={(e) => setSeries(e.target.value)} className="select">
                                {SERIES.map((item) => (
                                    <option key={item} value={item}>{item}</option>
                                ))}
                            </select>
                        </div>
                    </section>

                    <aside className="card summary-card">
                        <h2 className="section-title">선택 요약</h2>
                        <div className="summary-list">
                            <div className="summary-item">
                                <span className="summary-key">년도</span>
                                <span className="summary-value">{year}</span>
                            </div>
                            <div className="summary-item">
                                <span className="summary-key">과목</span>
                                <span className="summary-value">{subject}</span>
                            </div>
                            <div className="summary-item">
                                <span className="summary-key">회차</span>
                                <span className="summary-value">{series}</span>
                            </div>
                        </div>

                        <button className="start-btn" disabled={!canStart} onClick={handleStart}>
                            선택한 조건으로 시작하기
                        </button>
                        <p className="hint">선택한 조건으로 문제를 불러와 바로 풀이 화면으로 이동합니다.</p>
                    </aside>
                </div>
            </div>

            <div className="bottom-nav">
                <a href="/test_exam" className="nav-link">모의고사</a>
                <span className="nav-divider">·</span>
                <a href="/chat" className="nav-link">채팅으로</a>
                <span className="nav-divider">·</span>
                <a href="/" className="nav-link">홈으로</a>
            </div>

            <style jsx>{`
                .exam-container {
                    position: relative;
                    width: 100vw;
                    min-height: 100vh;
                    background: #000;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    overflow-x: hidden;
                    font-family: "Gothic A1", "Noto Sans KR", "Malgun Gothic", "맑은 고딕", sans-serif;
                }

                .particles { position: fixed; inset: 0; pointer-events: none; z-index: 0; }
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
                    0% { transform: translateY(0) scale(1); opacity: 0; }
                    10% { opacity: 0.4; }
                    90% { opacity: 0.1; }
                    100% { transform: translateY(-100vh) scale(0.3); opacity: 0; }
                }

                .top-logo {
                    position: fixed;
                    top: 28px;
                    left: 32px;
                    display: flex;
                    gap: 2px;
                    text-decoration: none;
                    font-size: 1.2rem;
                    font-weight: 900;
                    color: #fff;
                    letter-spacing: 0.05em;
                    z-index: 100;
                }

                .content {
                    position: relative;
                    z-index: 1;
                    width: 100%;
                    max-width: 1180px;
                    padding: 90px 24px 96px;
                    display: flex;
                    flex-direction: column;
                    gap: 24px;
                    animation: fadeIn 0.5s ease-out;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                .title-wrap { display: flex; flex-direction: column; gap: 8px; }
                .kicker {
                    margin: 0;
                    color: rgba(255, 255, 255, 0.35);
                    font-size: 0.78rem;
                    letter-spacing: 0.12em;
                }
                .title {
                    margin: 0;
                    color: rgba(255, 255, 255, 0.92);
                    font-size: 2rem;
                    letter-spacing: 0.05em;
                }
                .subtitle {
                    margin: 0;
                    color: rgba(255, 255, 255, 0.45);
                    font-size: 0.9rem;
                    letter-spacing: 0.02em;
                }

                .layout {
                    display: grid;
                    grid-template-columns: 1fr 320px;
                    gap: 16px;
                    align-items: start;
                }

                .card {
                    border-radius: 14px;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    background: rgba(255, 255, 255, 0.02);
                    backdrop-filter: blur(10px);
                }

                .form-card { padding: 20px; }
                .summary-card {
                    position: sticky;
                    top: 92px;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 14px;
                }

                .section-title {
                    margin: 0 0 10px 0;
                    font-size: 0.95rem;
                    letter-spacing: 0.08em;
                    color: rgba(255, 255, 255, 0.82);
                }

                .field { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
                .label {
                    font-size: 0.72rem;
                    color: rgba(255, 255, 255, 0.42);
                    letter-spacing: 0.06em;
                }

                .chip-grid {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                }
                .chip-grid.wide .chip { min-width: 84px; }

                .chip {
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    background: rgba(255, 255, 255, 0.02);
                    color: rgba(255, 255, 255, 0.6);
                    border-radius: 9px;
                    padding: 8px 12px;
                    font-size: 0.78rem;
                    font-family: inherit;
                    letter-spacing: 0.03em;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                .chip:hover {
                    color: rgba(255, 255, 255, 0.9);
                    border-color: rgba(255, 255, 255, 0.25);
                    background: rgba(255, 255, 255, 0.08);
                }
                .chip.active {
                    color: #fff;
                    border-color: rgba(59, 130, 246, 0.6);
                    background: rgba(59, 130, 246, 0.18);
                    box-shadow: inset 0 0 10px rgba(59, 130, 246, 0.12);
                }

                .row {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                }

                .select {
                    width: 100%;
                    border-radius: 9px;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    background: rgba(255, 255, 255, 0.03);
                    color: rgba(255, 255, 255, 0.8);
                    padding: 10px 12px;
                    font-size: 0.82rem;
                    font-family: inherit;
                    outline: none;
                }
                .select option {
                    color: #111;
                    background: #fff;
                }

                .summary-list {
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 10px;
                    overflow: hidden;
                }
                .summary-item {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 10px;
                    padding: 10px 12px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                }
                .summary-item:last-child { border-bottom: none; }
                .summary-key {
                    font-size: 0.72rem;
                    color: rgba(255, 255, 255, 0.35);
                    letter-spacing: 0.04em;
                }
                .summary-value {
                    font-size: 0.78rem;
                    color: rgba(255, 255, 255, 0.85);
                    font-weight: 600;
                    letter-spacing: 0.03em;
                }

                .start-btn {
                    width: 100%;
                    margin-top: 2px;
                    border: 1px solid rgba(59, 130, 246, 0.45);
                    background: rgba(59, 130, 246, 0.2);
                    color: rgba(255, 255, 255, 0.95);
                    border-radius: 10px;
                    padding: 12px 14px;
                    font-size: 0.86rem;
                    font-weight: 600;
                    font-family: inherit;
                    letter-spacing: 0.04em;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                .start-btn:hover:enabled {
                    background: rgba(59, 130, 246, 0.32);
                    border-color: rgba(59, 130, 246, 0.7);
                    transform: translateY(-1px);
                }
                .start-btn:disabled {
                    opacity: 0.35;
                    cursor: not-allowed;
                }
                .hint {
                    margin: 2px 0 0;
                    font-size: 0.72rem;
                    line-height: 1.6;
                    color: rgba(255, 255, 255, 0.32);
                    letter-spacing: 0.02em;
                }

                .bottom-nav {
                    position: relative;
                    z-index: 10;
                    padding: 0 0 28px;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                .nav-link {
                    color: rgba(255, 255, 255, 0.2);
                    font-size: 0.72rem;
                    letter-spacing: 0.05em;
                    text-decoration: none;
                    transition: color 0.2s ease;
                }
                .nav-link:hover { color: rgba(255, 255, 255, 0.6); }
                .nav-divider {
                    color: rgba(255, 255, 255, 0.1);
                    font-size: 0.7rem;
                }

                @media (max-width: 980px) {
                    .layout { grid-template-columns: 1fr; }
                    .summary-card {
                        position: static;
                        top: auto;
                    }
                }

                @media (max-width: 640px) {
                    .content { padding: 86px 16px 80px; }
                    .title { font-size: 1.5rem; }
                    .subtitle { font-size: 0.82rem; }
                    .row { grid-template-columns: 1fr; }
                    .form-card, .summary-card { padding: 14px; }
                    .chip { font-size: 0.74rem; }
                }
            `}</style>
        </div>
    );
}

