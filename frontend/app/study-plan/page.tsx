"use client";

import { useState, useEffect } from "react";
import { logout } from "@/lib/auth-api";
import { useUser } from "@/lib/hooks/useUser";

// ============================================================================
// 타입 정의
// ============================================================================

type SubjectStat = {
    subject: string;
    total: number;
    correct: number;
    wrong: number;
    accuracy: number;
    avg_time: number;
};

type TrendItem = {
    date: string;
    total: number;
    correct: number;
    score: number;
    avg_time: number;
};

type WrongDistItem = {
    subject: string;
    wrong_count: number;
    percentage: number;
};

type SlowQuestion = {
    question_id: number;
    subject: string;
    question_no: number;
    time_spent: number;
    is_correct: boolean;
};

type RepeatedWrong = {
    question_id: number;
    subject: string;
    question_no: number;
    question_preview: string;
    wrong_count: number;
};

type Analysis = {
    user_id: number;
    has_data: boolean;
    total_solved?: number;
    overall_accuracy?: number;
    overall_avg_time?: number;
    subject_stats?: SubjectStat[];
    weak_subjects?: SubjectStat[];
    strong_subjects?: SubjectStat[];
    slow_questions?: SlowQuestion[];
    repeated_wrong?: RepeatedWrong[];
    trend?: TrendItem[];
    wrong_distribution?: WrongDistItem[];
    message?: string;
};

type PlanJson = {
    summary?: string;
    priority_subjects?: string[];
    weekly_schedule?: {
        day: string;
        subjects: string[];
        focus?: string;
        hours?: number;
    }[];
    specific_advice?: string[];
    motivation?: string;
    generated_by?: string;
    raw_answer?: string;
    parse_failed?: boolean;
};

// ============================================================================
// 메인 컴포넌트
// ============================================================================

export default function StudyPlanPage() {
    const { user: loggedInUser, loading: userLoading } = useUser();
    const [userId, setUserId] = useState("");
    const [analysis, setAnalysis] = useState<Analysis | null>(null);
    const [planJson, setPlanJson] = useState<PlanJson | null>(null);
    const [generationMethod, setGenerationMethod] = useState<string | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isLoadingPlan, setIsLoadingPlan] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<"analysis" | "plan">("analysis");

    // 로그인된 사용자 ID 자동 설정
    useEffect(() => {
        if (loggedInUser?.id) {
            setUserId(String(loggedInUser.id));
        }
    }, [loggedInUser]);

    const handleLogout = async () => {
        const success = await logout();
        if (success) {
            window.location.href = "/login";
        } else {
            alert("로그아웃에 실패했습니다.");
        }
    };

    // 풀이 로그 분석만
    const handleAnalyze = async () => {
        setIsAnalyzing(true);
        setError(null);
        try {
            const res = await fetch("/api/study-plan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "analyze", user_id: parseInt(userId) }),
            });
            const data = await res.json();
            if (data.success && data.analysis) {
                setAnalysis(data.analysis);
                setActiveTab("analysis");
            } else {
                setError(data.error || "분석에 실패했습니다.");
            }
        } catch (e) {
            setError("서버에 연결할 수 없습니다.");
        } finally {
            setIsAnalyzing(false);
        }
    };

    // AI 학습 계획 생성 (분석 + RAG + EXAONE)
    const handleGenerate = async () => {
        setIsGenerating(true);
        setError(null);
        try {
            const res = await fetch("/api/study-plan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "generate",
                    user_id: parseInt(userId),
                    question: "내 풀이 데이터를 분석해서 최적의 학습 계획을 세워줘",
                }),
            });
            const data = await res.json();
            if (data.success) {
                // 분석 결과도 함께 업데이트
                if (data.analysis) setAnalysis(data.analysis);
                // plan_json 추출
                const plan = data.study_plan || data.plan;
                if (plan?.plan_json) {
                    setPlanJson(plan.plan_json);
                } else if (data.plan_json) {
                    setPlanJson(data.plan_json);
                }
                setGenerationMethod(data.generation_method || "template");
                setActiveTab("plan");
            } else {
                setError(data.error || "학습 계획 생성에 실패했습니다.");
            }
        } catch (e) {
            setError("서버에 연결할 수 없습니다.");
        } finally {
            setIsGenerating(false);
        }
    };

    // 기존 학습 계획 조회
    const handleLoadPlan = async () => {
        setIsLoadingPlan(true);
        setError(null);
        try {
            const res = await fetch("/api/study-plan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "read_latest", user_id: parseInt(userId) }),
            });
            const data = await res.json();
            if (data.success && data.study_plan) {
                const plan = data.study_plan;
                if (plan.plan_json) {
                    setPlanJson(plan.plan_json);
                    setGenerationMethod(plan.plan_json.generated_by || "unknown");
                    setActiveTab("plan");
                } else {
                    setError("학습 계획 데이터가 비어 있습니다.");
                }
            } else {
                setError(data.error || "생성된 학습 계획이 없습니다.");
            }
        } catch (e) {
            setError("서버에 연결할 수 없습니다.");
        } finally {
            setIsLoadingPlan(false);
        }
    };

    // 정답률 기반 색상
    const getAccuracyColor = (accuracy: number) => {
        if (accuracy >= 80) return "#4ade80";
        if (accuracy >= 60) return "#facc15";
        if (accuracy >= 40) return "#fb923c";
        return "#f87171";
    };

    return (
        <div className="page-container">
            {/* 헤더 */}
            <header className="page-header">
                <div className="header-left">
                    <a href="/chat" className="back-link">← 채팅</a>
                    <h1 className="page-title">학습 분석 & AI 플랜</h1>
                </div>
                <div className="header-right">
                    <a href="/" className="home-link">홈</a>
                    <button onClick={handleLogout} className="logout-link">로그아웃</button>
                </div>
            </header>

            {/* 사용자 선택 + 액션 버튼 */}
            <div className="action-bar">
                <div className="user-input-group">
                    <label className="input-label">
                        {loggedInUser?.display_name
                            ? `${loggedInUser.display_name} 님`
                            : userLoading ? "로딩 중..." : "사용자 ID"}
                    </label>
                    <input
                        type="number"
                        value={userId}
                        onChange={(e) => setUserId(e.target.value)}
                        className="user-input"
                        min="1"
                        readOnly={!!loggedInUser?.id}
                        style={loggedInUser?.id ? { opacity: 0.7, cursor: "default" } : {}}
                    />
                </div>
                <button
                    onClick={handleAnalyze}
                    disabled={isAnalyzing || isGenerating || isLoadingPlan}
                    className="btn btn-analyze"
                >
                    {isAnalyzing ? "분석 중..." : "📊 풀이 분석"}
                </button>
                <button
                    onClick={handleLoadPlan}
                    disabled={isAnalyzing || isGenerating || isLoadingPlan}
                    className="btn btn-load-plan"
                >
                    {isLoadingPlan ? "조회 중..." : "📋 학습 계획"}
                </button>
                <span className="generate-wrapper">
                    <button
                        onClick={handleGenerate}
                        disabled={isAnalyzing || isGenerating || isLoadingPlan || !analysis?.has_data}
                        className="btn btn-generate"
                    >
                        {isGenerating ? "생성 중..." : "🤖 AI 플랜 생성"}
                    </button>
                    {!analysis?.has_data && (
                        <span className="generate-tooltip">풀이 분석을 먼저 진행해주세요</span>
                    )}
                </span>
            </div>

            {/* 에러 표시 */}
            {error && <div className="error-msg">{error}</div>}

            {/* 구분선 */}
            {(analysis || planJson) && (
                <div style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }} />
            )}

            {/* ============================================================ */}
            {/* 분석 결과 탭 */}
            {/* ============================================================ */}
            {activeTab === "analysis" && analysis && (
                <div className="content">
                    {!analysis.has_data ? (
                        <div className="empty-state">
                            <p className="empty-icon">📭</p>
                            <p>{analysis.message || "풀이 기록이 없습니다."}</p>
                            <p className="empty-sub">모의고사를 먼저 풀어주세요!</p>
                        </div>
                    ) : (
                        <>
                            {/* 전체 요약 카드 */}
                            <div className="summary-cards">
                                <div className="card summary-card">
                                    <div className="card-label">총 풀이</div>
                                    <div className="card-value">{analysis.total_solved}문제</div>
                                </div>
                                <div className="card summary-card">
                                    <div className="card-label">전체 정답률</div>
                                    <div
                                        className="card-value"
                                        style={{ color: getAccuracyColor(analysis.overall_accuracy || 0) }}
                                    >
                                        {analysis.overall_accuracy?.toFixed(1)}%
                                    </div>
                                </div>
                                <div className="card summary-card">
                                    <div className="card-label">평균 풀이시간</div>
                                    <div className="card-value">{analysis.overall_avg_time?.toFixed(0)}초</div>
                                </div>
                            </div>

                            {/* 과목별 정답률 */}
                            {analysis.subject_stats && analysis.subject_stats.length > 0 && (
                                <div className="card section-card">
                                    <h3 className="section-title">📚 과목별 정답률</h3>
                                    <div className="subject-bars">
                                        {analysis.subject_stats.map((s) => (
                                            <div key={s.subject} className="subject-row">
                                                <div className="subject-name">{s.subject}</div>
                                                <div className="bar-container">
                                                    <div
                                                        className="bar-fill"
                                                        style={{
                                                            width: `${s.accuracy}%`,
                                                            background: getAccuracyColor(s.accuracy),
                                                        }}
                                                    />
                                                </div>
                                                <div className="subject-stat">
                                                    <span style={{ color: getAccuracyColor(s.accuracy) }}>
                                                        {s.accuracy.toFixed(0)}%
                                                    </span>
                                                    <span className="stat-detail">
                                                        ({s.correct}/{s.total})
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* 취약/강점 과목 */}
                            <div className="two-col">
                                {analysis.weak_subjects && analysis.weak_subjects.length > 0 && (
                                    <div className="card section-card">
                                        <h3 className="section-title">⚠️ 취약 과목</h3>
                                        {analysis.weak_subjects.map((s) => (
                                            <div key={s.subject} className="insight-item weak">
                                                <span className="insight-subject">{s.subject}</span>
                                                <span className="insight-value" style={{ color: "#f87171" }}>
                                                    {s.accuracy.toFixed(0)}%
                                                </span>
                                                <span className="insight-detail">
                                                    평균 {s.avg_time.toFixed(0)}초
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                                {analysis.strong_subjects && analysis.strong_subjects.length > 0 && (
                                    <div className="card section-card">
                                        <h3 className="section-title">✅ 강점 과목</h3>
                                        {analysis.strong_subjects.map((s) => (
                                            <div key={s.subject} className="insight-item strong">
                                                <span className="insight-subject">{s.subject}</span>
                                                <span className="insight-value" style={{ color: "#4ade80" }}>
                                                    {s.accuracy.toFixed(0)}%
                                                </span>
                                                <span className="insight-detail">
                                                    평균 {s.avg_time.toFixed(0)}초
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* 점수 추이 */}
                            {analysis.trend && analysis.trend.length > 0 && (
                                <div className="card section-card">
                                    <h3 className="section-title">📈 점수 추이</h3>
                                    <div className="trend-list">
                                        {analysis.trend.map((t) => (
                                            <div key={t.date} className="trend-item">
                                                <span className="trend-date">{t.date}</span>
                                                <div className="trend-bar-container">
                                                    <div
                                                        className="trend-bar"
                                                        style={{
                                                            width: `${t.score}%`,
                                                            background: getAccuracyColor(t.score),
                                                        }}
                                                    />
                                                </div>
                                                <span className="trend-score" style={{ color: getAccuracyColor(t.score) }}>
                                                    {t.score.toFixed(0)}점
                                                </span>
                                                <span className="trend-detail">
                                                    ({t.correct}/{t.total})
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* 반복 오답 */}
                            {analysis.repeated_wrong && analysis.repeated_wrong.length > 0 && (
                                <div className="card section-card">
                                    <h3 className="section-title">🔄 반복 오답 문항</h3>
                                    {analysis.repeated_wrong.map((rw) => (
                                        <div key={rw.question_id} className="repeated-item">
                                            <span className="repeated-badge">{rw.wrong_count}회</span>
                                            <span className="repeated-subject">{rw.subject}</span>
                                            <span className="repeated-no">{rw.question_no}번</span>
                                            <span className="repeated-preview">{rw.question_preview}</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* 오답 과목 분포 */}
                            {analysis.wrong_distribution && analysis.wrong_distribution.length > 0 && (
                                <div className="card section-card">
                                    <h3 className="section-title">🎯 오답 과목 분포</h3>
                                    <div className="dist-list">
                                        {analysis.wrong_distribution.map((wd) => (
                                            <div key={wd.subject} className="dist-item">
                                                <span className="dist-subject">{wd.subject}</span>
                                                <div className="dist-bar-container">
                                                    <div
                                                        className="dist-bar"
                                                        style={{
                                                            width: `${wd.percentage}%`,
                                                            background: "#f87171",
                                                        }}
                                                    />
                                                </div>
                                                <span className="dist-value">
                                                    {wd.wrong_count}개 ({wd.percentage.toFixed(0)}%)
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* ============================================================ */}
            {/* 학습 계획 탭 */}
            {/* ============================================================ */}
            {activeTab === "plan" && planJson && (
                <div className="content">
                    {/* 생성 방식 뱃지 */}
                    <div className="method-badge">
                        {generationMethod === "exaone" ? "🤖 EXAONE 생성" : "📋 템플릿 생성"}
                    </div>

                    {/* 요약 */}
                    {planJson.summary && (
                        <div className="card section-card">
                            <h3 className="section-title">📝 분석 요약</h3>
                            <p className="plan-summary">{planJson.summary}</p>
                        </div>
                    )}

                    {/* 우선 보강 과목 */}
                    {planJson.priority_subjects && planJson.priority_subjects.length > 0 && (
                        <div className="card section-card">
                            <h3 className="section-title">📌 우선 보강 과목</h3>
                            <div className="priority-list">
                                {planJson.priority_subjects.map((subj, i) => (
                                    <span key={subj} className="priority-chip">
                                        {i + 1}. {subj}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 주간 스케줄 */}
                    {planJson.weekly_schedule && planJson.weekly_schedule.length > 0 && (
                        <div className="card section-card">
                            <h3 className="section-title">🗓️ 주간 학습 스케줄</h3>
                            <div className="schedule-grid">
                                {planJson.weekly_schedule.map((day) => (
                                    <div key={day.day} className="schedule-item">
                                        <div className="schedule-day">{day.day}</div>
                                        <div className="schedule-subjects">
                                            {day.subjects.map((s) => (
                                                <span key={s} className="schedule-subject-chip">
                                                    {s}
                                                </span>
                                            ))}
                                        </div>
                                        {day.focus && (
                                            <div className="schedule-focus">{day.focus}</div>
                                        )}
                                        {day.hours && (
                                            <div className="schedule-hours">{day.hours}시간</div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 학습 조언 */}
                    {planJson.specific_advice && planJson.specific_advice.length > 0 && (
                        <div className="card section-card">
                            <h3 className="section-title">💡 학습 조언</h3>
                            <ol className="advice-list">
                                {planJson.specific_advice.map((advice, i) => (
                                    <li key={i} className="advice-item">{advice}</li>
                                ))}
                            </ol>
                        </div>
                    )}

                    {/* 동기부여 */}
                    {planJson.motivation && (
                        <div className="card motivation-card">
                            <p className="motivation-text">{planJson.motivation}</p>
                        </div>
                    )}

                    {/* EXAONE 원본 응답 (JSON 파싱 실패 시) */}
                    {planJson.parse_failed && planJson.raw_answer && (
                        <div className="card section-card">
                            <h3 className="section-title">💬 AI 원본 응답</h3>
                            <pre className="raw-answer">{planJson.raw_answer}</pre>
                        </div>
                    )}

                    {/* 내용이 비어있을 때 안내 */}
                    {!planJson.summary && !planJson.priority_subjects?.length && !planJson.weekly_schedule?.length && !planJson.raw_answer && (
                        <div className="empty-state">
                            <p className="empty-icon">📋</p>
                            <p>학습 계획 내용이 비어 있습니다.</p>
                            <p className="empty-sub">
                                AI 플랜을 다시 생성해주세요. 풀이 분석 후 AI 플랜 생성 버튼을 눌러주세요.
                            </p>
                        </div>
                    )}
                </div>
            )}

            <style jsx>{`
                .page-container {
                    min-height: 100vh;
                    background: #000;
                    color: #fff;
                    font-family: "Gothic A1", "Noto Sans KR", "Malgun Gothic", sans-serif;
                    padding: 0;
                }

                /* ── 헤더 ── */
                .page-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 20px 32px;
                    border-bottom: 1px solid rgba(255,255,255,0.04);
                }
                .header-left { display: flex; align-items: center; gap: 16px; }
                .header-right { display: flex; align-items: center; gap: 14px; }
                .back-link, .home-link {
                    color: rgba(255,255,255,0.35);
                    text-decoration: none;
                    font-size: 0.8rem;
                    transition: color 0.2s;
                }
                .back-link:hover, .home-link:hover { color: rgba(255,255,255,0.7); }

                .logout-link {
                    color: rgba(255,100,100,0.5);
                    background: none;
                    border: none;
                    font-size: 0.8rem;
                    font-family: inherit;
                    cursor: pointer;
                    transition: color 0.2s;
                    padding: 0;
                }
                .logout-link:hover { color: rgba(255,100,100,0.9); }
                .page-title {
                    font-size: 1.1rem;
                    font-weight: 600;
                    color: rgba(255,255,255,0.9);
                    margin: 0;
                }

                /* ── 액션바 ── */
                .action-bar {
                    display: flex;
                    align-items: flex-end;
                    gap: 12px;
                    padding: 20px 32px;
                    border-bottom: 1px solid rgba(255,255,255,0.04);
                }
                .user-input-group { display: flex; flex-direction: column; gap: 4px; }
                .input-label {
                    font-size: 0.65rem;
                    color: rgba(255,255,255,0.3);
                    letter-spacing: 0.1em;
                }
                .user-input {
                    width: 80px;
                    padding: 8px 12px;
                    border-radius: 8px;
                    border: 1px solid rgba(255,255,255,0.08);
                    background: rgba(255,255,255,0.03);
                    color: #fff;
                    font-size: 0.85rem;
                    outline: none;
                }
                .user-input:focus { border-color: rgba(255,255,255,0.2); }

                .btn {
                    padding: 8px 20px;
                    border-radius: 8px;
                    border: none;
                    font-size: 0.82rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s;
                    letter-spacing: 0.02em;
                }
                .btn:disabled { opacity: 0.4; cursor: not-allowed; }
                .btn-analyze {
                    background: rgba(59,130,246,0.15);
                    color: #60a5fa;
                    border: 1px solid rgba(59,130,246,0.2);
                }
                .btn-analyze:hover:not(:disabled) {
                    background: rgba(59,130,246,0.25);
                }
                .btn-generate {
                    background: rgba(168,85,247,0.15);
                    color: #c084fc;
                    border: 1px solid rgba(168,85,247,0.2);
                }
                .btn-generate:hover:not(:disabled) {
                    background: rgba(168,85,247,0.25);
                }
                .btn-load-plan {
                    background: rgba(34,197,94,0.15);
                    color: #4ade80;
                    border: 1px solid rgba(34,197,94,0.2);
                }
                .btn-load-plan:hover:not(:disabled) {
                    background: rgba(34,197,94,0.25);
                }
                .generate-wrapper {
                    position: relative;
                    display: inline-block;
                }
                .generate-wrapper:hover .generate-tooltip {
                    opacity: 1;
                    visibility: visible;
                    transform: translateX(-50%) translateY(0);
                }
                .generate-tooltip {
                    position: absolute;
                    bottom: calc(100% + 8px);
                    left: 50%;
                    transform: translateX(-50%) translateY(4px);
                    white-space: nowrap;
                    padding: 6px 14px;
                    border-radius: 6px;
                    background: rgba(30,30,30,0.95);
                    border: 1px solid rgba(255,255,255,0.12);
                    color: rgba(255,255,255,0.7);
                    font-size: 0.72rem;
                    opacity: 0;
                    visibility: hidden;
                    transition: all 0.2s ease;
                    pointer-events: none;
                    z-index: 10;
                }
                .generate-tooltip::after {
                    content: "";
                    position: absolute;
                    top: 100%;
                    left: 50%;
                    transform: translateX(-50%);
                    border: 5px solid transparent;
                    border-top-color: rgba(255,255,255,0.12);
                }

                /* ── 에러 ── */
                .error-msg {
                    margin: 12px 32px;
                    padding: 10px 16px;
                    border-radius: 8px;
                    background: rgba(239,68,68,0.1);
                    border: 1px solid rgba(239,68,68,0.2);
                    color: #fca5a5;
                    font-size: 0.8rem;
                }

                /* ── 탭 ── */
                .tab-bar {
                    display: flex;
                    gap: 4px;
                    padding: 12px 32px 0;
                }
                .tab {
                    padding: 8px 18px;
                    border-radius: 8px 8px 0 0;
                    border: none;
                    background: rgba(255,255,255,0.03);
                    color: rgba(255,255,255,0.35);
                    font-size: 0.8rem;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .tab:hover:not(:disabled) { color: rgba(255,255,255,0.6); }
                .tab.active {
                    background: rgba(255,255,255,0.06);
                    color: rgba(255,255,255,0.9);
                }
                .tab:disabled { opacity: 0.3; cursor: not-allowed; }

                /* ── 콘텐츠 ── */
                .content { padding: 20px 32px 40px; }

                /* ── 빈 상태 ── */
                .empty-state {
                    text-align: center;
                    padding: 60px 20px;
                    color: rgba(255,255,255,0.3);
                }
                .empty-icon { font-size: 3rem; margin-bottom: 12px; }
                .empty-sub { font-size: 0.75rem; margin-top: 8px; }

                /* ── 카드 ── */
                .card {
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.05);
                    border-radius: 12px;
                    padding: 18px 20px;
                }

                /* ── 요약 카드 ── */
                .summary-cards {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 12px;
                    margin-bottom: 16px;
                }
                .summary-card { text-align: center; }
                .card-label {
                    font-size: 0.65rem;
                    color: rgba(255,255,255,0.3);
                    letter-spacing: 0.1em;
                    margin-bottom: 6px;
                }
                .card-value {
                    font-size: 1.4rem;
                    font-weight: 700;
                    color: rgba(255,255,255,0.85);
                }

                /* ── 섹션 카드 ── */
                .section-card { margin-bottom: 16px; }
                .section-title {
                    font-size: 0.85rem;
                    font-weight: 600;
                    color: rgba(255,255,255,0.7);
                    margin: 0 0 14px 0;
                }

                /* ── 과목별 바 ── */
                .subject-bars { display: flex; flex-direction: column; gap: 10px; }
                .subject-row { display: flex; align-items: center; gap: 12px; }
                .subject-name {
                    width: 80px;
                    font-size: 0.78rem;
                    color: rgba(255,255,255,0.6);
                    flex-shrink: 0;
                }
                .bar-container {
                    flex: 1;
                    height: 8px;
                    background: rgba(255,255,255,0.04);
                    border-radius: 4px;
                    overflow: hidden;
                }
                .bar-fill {
                    height: 100%;
                    border-radius: 4px;
                    transition: width 0.6s ease;
                }
                .subject-stat {
                    width: 100px;
                    text-align: right;
                    font-size: 0.78rem;
                    flex-shrink: 0;
                }
                .stat-detail {
                    color: rgba(255,255,255,0.25);
                    margin-left: 4px;
                    font-size: 0.7rem;
                }

                /* ── 2열 레이아웃 ── */
                .two-col {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                }

                /* ── 인사이트 아이템 ── */
                .insight-item {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 8px 0;
                    border-bottom: 1px solid rgba(255,255,255,0.03);
                }
                .insight-item:last-child { border-bottom: none; }
                .insight-subject { font-size: 0.8rem; color: rgba(255,255,255,0.7); flex: 1; }
                .insight-value { font-size: 0.85rem; font-weight: 600; }
                .insight-detail { font-size: 0.7rem; color: rgba(255,255,255,0.25); }

                /* ── 추이 ── */
                .trend-list { display: flex; flex-direction: column; gap: 8px; }
                .trend-item { display: flex; align-items: center; gap: 10px; }
                .trend-date {
                    width: 90px;
                    font-size: 0.72rem;
                    color: rgba(255,255,255,0.35);
                    flex-shrink: 0;
                }
                .trend-bar-container {
                    flex: 1;
                    height: 6px;
                    background: rgba(255,255,255,0.04);
                    border-radius: 3px;
                    overflow: hidden;
                }
                .trend-bar { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
                .trend-score { font-size: 0.78rem; font-weight: 600; width: 45px; text-align: right; }
                .trend-detail { font-size: 0.68rem; color: rgba(255,255,255,0.2); width: 50px; }

                /* ── 반복 오답 ── */
                .repeated-item {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px 0;
                    border-bottom: 1px solid rgba(255,255,255,0.03);
                    font-size: 0.78rem;
                }
                .repeated-item:last-child { border-bottom: none; }
                .repeated-badge {
                    background: rgba(239,68,68,0.15);
                    color: #f87171;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 0.7rem;
                    font-weight: 600;
                }
                .repeated-subject { color: rgba(255,255,255,0.5); }
                .repeated-no { color: rgba(255,255,255,0.4); }
                .repeated-preview {
                    flex: 1;
                    color: rgba(255,255,255,0.25);
                    overflow: hidden;
                    white-space: nowrap;
                    text-overflow: ellipsis;
                }

                /* ── 오답 분포 ── */
                .dist-list { display: flex; flex-direction: column; gap: 8px; }
                .dist-item { display: flex; align-items: center; gap: 10px; }
                .dist-subject {
                    width: 80px;
                    font-size: 0.78rem;
                    color: rgba(255,255,255,0.6);
                    flex-shrink: 0;
                }
                .dist-bar-container {
                    flex: 1;
                    height: 6px;
                    background: rgba(255,255,255,0.04);
                    border-radius: 3px;
                    overflow: hidden;
                }
                .dist-bar { height: 100%; border-radius: 3px; }
                .dist-value {
                    font-size: 0.72rem;
                    color: rgba(255,255,255,0.35);
                    width: 90px;
                    text-align: right;
                }

                /* ── 학습 계획: 생성 방식 뱃지 ── */
                .method-badge {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 6px;
                    background: rgba(168,85,247,0.1);
                    border: 1px solid rgba(168,85,247,0.2);
                    color: #c084fc;
                    font-size: 0.72rem;
                    margin-bottom: 16px;
                }

                /* ── 계획 요약 ── */
                .plan-summary {
                    font-size: 0.85rem;
                    color: rgba(255,255,255,0.6);
                    line-height: 1.6;
                    margin: 0;
                }

                /* ── 우선 과목 ── */
                .priority-list { display: flex; flex-wrap: wrap; gap: 8px; }
                .priority-chip {
                    padding: 6px 14px;
                    border-radius: 6px;
                    background: rgba(251,146,60,0.1);
                    border: 1px solid rgba(251,146,60,0.2);
                    color: #fb923c;
                    font-size: 0.78rem;
                    font-weight: 500;
                }

                /* ── 주간 스케줄 ── */
                .schedule-grid {
                    display: grid;
                    grid-template-columns: repeat(7, 1fr);
                    gap: 8px;
                }
                .schedule-item {
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.04);
                    border-radius: 8px;
                    padding: 10px 8px;
                    text-align: center;
                }
                .schedule-day {
                    font-size: 0.75rem;
                    font-weight: 600;
                    color: rgba(255,255,255,0.6);
                    margin-bottom: 6px;
                }
                .schedule-subjects { display: flex; flex-direction: column; gap: 3px; }
                .schedule-subject-chip {
                    font-size: 0.65rem;
                    color: rgba(255,255,255,0.5);
                    background: rgba(59,130,246,0.08);
                    border-radius: 3px;
                    padding: 2px 4px;
                }
                .schedule-focus {
                    font-size: 0.6rem;
                    color: rgba(255,255,255,0.2);
                    margin-top: 4px;
                }
                .schedule-hours {
                    font-size: 0.65rem;
                    color: rgba(255,255,255,0.3);
                    margin-top: 2px;
                }

                /* ── 학습 조언 ── */
                .advice-list {
                    margin: 0;
                    padding-left: 20px;
                }
                .advice-item {
                    font-size: 0.82rem;
                    color: rgba(255,255,255,0.55);
                    line-height: 1.7;
                    margin-bottom: 4px;
                }

                /* ── 동기부여 카드 ── */
                .motivation-card {
                    background: rgba(168,85,247,0.05);
                    border: 1px solid rgba(168,85,247,0.1);
                    text-align: center;
                    margin-top: 16px;
                }
                .motivation-text {
                    font-size: 0.95rem;
                    color: rgba(255,255,255,0.7);
                    margin: 0;
                    line-height: 1.6;
                }

                /* ── 원본 응답 ── */
                .raw-answer {
                    font-size: 0.75rem;
                    color: rgba(255,255,255,0.4);
                    background: rgba(255,255,255,0.02);
                    padding: 12px;
                    border-radius: 6px;
                    white-space: pre-wrap;
                    overflow-x: auto;
                }

                /* ── 반응형 (태블릿) ── */
                @media (max-width: 768px) {
                    .summary-cards { grid-template-columns: 1fr; }
                    .two-col { grid-template-columns: 1fr; }
                    .schedule-grid { grid-template-columns: repeat(3, 1fr); }
                    .action-bar { flex-wrap: wrap; }
                    .page-header { padding: 16px 20px; }
                    .action-bar { padding: 16px 20px; }
                    .content { padding: 16px 20px 32px; }
                    .error-msg { margin: 12px 20px; }
                }

                /* ── 반응형 (모바일) ── */
                @media (max-width: 480px) {
                    .page-header {
                        padding: 12px 14px;
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 8px;
                    }
                    .header-left {
                        gap: 10px;
                        width: 100%;
                    }
                    .header-right {
                        align-self: flex-end;
                        margin-top: -24px;
                    }
                    .page-title {
                        font-size: 0.95rem;
                    }
                    .action-bar {
                        padding: 12px 14px;
                        gap: 8px;
                        flex-wrap: wrap;
                    }
                    .user-input-group {
                        flex-direction: row;
                        align-items: center;
                        gap: 8px;
                    }
                    .user-input {
                        width: 60px;
                        padding: 6px 10px;
                        font-size: 0.8rem;
                    }
                    .btn {
                        padding: 7px 14px;
                        font-size: 0.75rem;
                    }
                    .content {
                        padding: 12px 14px 28px;
                    }
                    .card {
                        padding: 14px 14px;
                    }
                    .card-value {
                        font-size: 1.2rem;
                    }
                    .subject-name {
                        width: 60px;
                        font-size: 0.72rem;
                    }
                    .subject-stat {
                        width: 80px;
                        font-size: 0.72rem;
                    }
                    .schedule-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                    .trend-date {
                        width: 70px;
                        font-size: 0.65rem;
                    }
                    .trend-detail {
                        display: none;
                    }
                    .repeated-item {
                        flex-wrap: wrap;
                        font-size: 0.72rem;
                    }
                    .repeated-preview {
                        width: 100%;
                        font-size: 0.68rem;
                    }
                    .dist-subject {
                        width: 60px;
                        font-size: 0.72rem;
                    }
                    .dist-value {
                        width: 70px;
                        font-size: 0.65rem;
                    }
                    .error-msg {
                        margin: 8px 14px;
                        font-size: 0.75rem;
                    }
                    .generate-tooltip {
                        font-size: 0.65rem;
                        padding: 5px 10px;
                    }
                    .priority-chip {
                        padding: 4px 10px;
                        font-size: 0.72rem;
                    }
                    .advice-item {
                        font-size: 0.78rem;
                    }
                    .motivation-text {
                        font-size: 0.85rem;
                    }
                }
            `}</style>
        </div>
    );
}

