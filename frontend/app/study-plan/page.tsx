"use client";

import { useState, useEffect } from "react";
import { logout, API_BASE_URL, authFetch } from "@/lib/auth-api";
import { useUser } from "@/lib/hooks/useUser";
import {
    GUEST_PROFILE_KEY,
    GUEST_SOLVING_LOGS_KEY,
    isGuestEntryActive,
} from "@/lib/guest-session";

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

type RagSource = {
    id: number;
    rank: number;
    similarity: number;
    final_score?: number;
    profile_bonus?: number;
    match_reasons?: string[];
    title: string;
    source_name?: string;
    source_url?: string;
    exam_info?: Record<string, unknown>;
    study_info?: string;
    method_subjects?: string[];
    context_preview?: string;
    key_points_preview?: string;
    difficulties_preview?: string;
    subject_methods_preview?: Record<string, string>;
};

type UserProfileSummary = {
    name?: string;
    age?: number;
    employment_status?: string;
    is_first_timer?: boolean;
    target_position?: string;
    weak_subjects?: string[];
    strong_subjects?: string[];
    daily_study_time?: number;
    study_duration?: string;
};

type SubjectPlan = {
    subject: string;
    current_level?: string;
    strategy?: string;
    recommended_materials?: string;
    weekly_hours?: number;
    priority?: string;
};

type DailyRoutine = {
    description?: string;
    morning?: string;
    afternoon?: string;
    evening?: string;
    review?: string;
};

type StudyMethod = {
    method: string;
    description: string;
    source_story?: string;
};

const NOISE_MARKERS = [
    "목록 다음글",
    "이전글",
    "회사소개",
    "이용약관",
    "개인정보처리방침",
    "copyright",
    "all rights reserved",
    "사업자등록번호",
    "통신판매업신고번호",
    "호스팅제공자",
    "원격평생교육시설",
    "대표이사",
    "개인정보보호책임자",
    "가입사실 확인",
    "서울특별시 구로구",
] as const;

const NOISE_REGEX_CUT_PATTERNS: RegExp[] = [
    /목록[\s\u00A0\u200B\u200C\u200D]*다음글[\s\S]*$/i,
    /이전글[\s\S]*$/i,
    /회사소개[\s\S]*$/i,
    /개인정보처리방침[\s\S]*$/i,
    /copyright[\s\S]*$/i,
    /all rights reserved[\s\S]*$/i,
    /사업자등록번호[\s\S]*$/i,
    /통신판매업신고번호[\s\S]*$/i,
    /호스팅제공자[\s\S]*$/i,
    /원격평생교육시설[\s\S]*$/i,
];

function sanitizeNoiseText(text: string): string {
    let cleaned = text
        .replace(/[\u200B-\u200D\uFEFF]/g, "") // zero-width chars
        .replace(/\u00A0/g, " ") // NBSP
        .trim();
    if (!cleaned) return "";

    // 1) 강한 컷오프 정규식 먼저 적용
    NOISE_REGEX_CUT_PATTERNS.forEach((pattern) => {
        cleaned = cleaned.replace(pattern, "").trim();
    });

    // 2) 마커 기반 보조 컷오프 (예상치 못한 변형 대응)
    const lower = cleaned.toLowerCase();
    const cutIndexes = NOISE_MARKERS
        .map((marker) => lower.indexOf(marker.toLowerCase()))
        .filter((idx) => idx >= 0);
    if (cutIndexes.length > 0) {
        cleaned = cleaned.slice(0, Math.min(...cutIndexes)).trim();
    }

    return cleaned;
}

function sanitizeDeep<T>(value: T): T {
    if (typeof value === "string") {
        return sanitizeNoiseText(value) as T;
    }
    if (Array.isArray(value)) {
        return value.map((item) => sanitizeDeep(item)) as T;
    }
    if (value && typeof value === "object") {
        const obj = value as Record<string, unknown>;
        const next: Record<string, unknown> = {};
        Object.entries(obj).forEach(([k, v]) => {
            next[k] = sanitizeDeep(v);
        });
        return next as T;
    }
    return value;
}

function normalizeForCompare(text: string): string {
    return text
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim();
}

function dedupeSubjectPlans(plans: SubjectPlan[]): SubjectPlan[] {
    const firstSubjectByStrategy = new Map<string, string>();
    return plans.map((sp) => {
        const strategy = (sp.strategy || "").trim();
        if (!strategy) return sp;

        const key = normalizeForCompare(strategy);
        const firstSubject = firstSubjectByStrategy.get(key);
        if (!firstSubject) {
            firstSubjectByStrategy.set(key, sp.subject);
            return sp;
        }
        return {
            ...sp,
            strategy: `${firstSubject} 학습법과 동일하여 중복 내용은 생략합니다.`,
        };
    });
}

function dedupeMethodPreviewEntries(
    preview: Record<string, string>,
): Array<[string, string]> {
    const firstSubjectByMethod = new Map<string, string>();
    const entries: Array<[string, string]> = [];

    Object.entries(preview).forEach(([subj, method]) => {
        const cleaned = (method || "").trim();
        if (!cleaned) return;

        const key = normalizeForCompare(cleaned);
        const firstSubject = firstSubjectByMethod.get(key);
        if (!firstSubject) {
            firstSubjectByMethod.set(key, subj);
            entries.push([subj, cleaned]);
            return;
        }
        entries.push([subj, `${firstSubject} 동일 내용 (중복 생략)`]);
    });

    return entries;
}

type PlanJson = {
    summary?: string;
    matched_stories_analysis?: string;
    priority_subjects?: string[];
    subject_plans?: SubjectPlan[];
    daily_routine?: DailyRoutine;
    weekly_schedule?: {
        day: string;
        subjects: string[];
        focus?: string;
        hours?: number;
    }[];
    study_methods?: StudyMethod[];
    difficulty_management?: string[];
    key_strategies?: string[];
    specific_advice?: string[];
    motivation?: string;
    generated_by?: string;
    raw_answer?: string;
    parse_failed?: boolean;
    rag_sources?: RagSource[];
    user_profile_applied?: boolean;
    user_profile_summary?: UserProfileSummary;
};

// ============================================================================
// 메인 컴포넌트
// ============================================================================

export default function StudyPlanPage() {
    const { user: loggedInUser, loading: userLoading } = useUser();
    const [guestEntry, setGuestEntry] = useState(false);
    const isGuest = !userLoading && !loggedInUser && guestEntry;

    const [userId, setUserId] = useState("");
    const [analysis, setAnalysis] = useState<Analysis | null>(null);
    const [planJson, setPlanJson] = useState<PlanJson | null>(null);
    const [generationMethod, setGenerationMethod] = useState<string | null>(null);
    const [ragSources, setRagSources] = useState<RagSource[]>([]);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isLoadingPlan, setIsLoadingPlan] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<"analysis" | "plan">("analysis");
    const [isProfileSet, setIsProfileSet] = useState(false);

    useEffect(() => {
        try {
            setGuestEntry(isGuestEntryActive());
        } catch {
            setGuestEntry(false);
        }
    }, []);

    // 로그인된 사용자 ID 자동 설정 + 프로필 설정 여부 확인
    useEffect(() => {
        if (userLoading) return;
        if (loggedInUser?.id) {
            setUserId(String(loggedInUser.id));
            (async () => {
                try {
                    const res = await authFetch(
                        `${API_BASE_URL}/api/v1/admin/users/${loggedInUser.id}`
                    );
                    if (res.ok) {
                        const data = await res.json();
                        if (data.success && data.user) {
                            const u = data.user;
                            const hasProfile = !!(
                                u.target_position ||
                                u.employment_status ||
                                u.is_first_timer !== null ||
                                u.study_duration ||
                                (u.weak_subjects && u.weak_subjects.trim()) ||
                                (u.strong_subjects && u.strong_subjects.trim())
                            );
                            setIsProfileSet(hasProfile);
                        }
                    }
                } catch {
                    /* ignore */
                }
            })();
            return;
        }
        if (isGuest) {
            setUserId("guest");
            try {
                const raw = localStorage.getItem(GUEST_PROFILE_KEY);
                if (raw) {
                    const g = JSON.parse(raw);
                    const hasProfile = !!(
                        g.target_position ||
                        g.employment_status ||
                        g.is_first_timer !== null ||
                        g.study_duration ||
                        (g.weak_subjects && String(g.weak_subjects).trim()) ||
                        (g.strong_subjects && String(g.strong_subjects).trim())
                    );
                    setIsProfileSet(hasProfile);
                }
            } catch {
                /* ignore */
            }
        }
    }, [userLoading, loggedInUser, isGuest]);

    const handleLogout = () => {
        logout(); // 백엔드 리다이렉트로 쿠키 삭제 + /login 이동
    };

    const loadGuestLogs = () => {
        try {
            const raw = sessionStorage.getItem(GUEST_SOLVING_LOGS_KEY);
            if (!raw) return null;
            const parsed = JSON.parse(raw) as { logs?: unknown };
            return parsed.logs as Array<{
                question_id: number;
                subject: string;
                selected_answer: string | null;
                answer_key: string | null;
                time_spent: number;
                is_correct: boolean;
                is_wrong_note: boolean;
            }> | null;
        } catch {
            return null;
        }
    };

    const computeGuestAnalysis = (
        logs: NonNullable<ReturnType<typeof loadGuestLogs>>,
    ): Analysis | null => {
        if (!logs?.length) return null;
        const subjectMap: Record<string, { total: number; correct: number; time: number }> = {};
        logs.forEach((l) => {
            const s = l.subject || "기타";
            if (!subjectMap[s]) subjectMap[s] = { total: 0, correct: 0, time: 0 };
            subjectMap[s].total++;
            if (l.is_correct) subjectMap[s].correct++;
            subjectMap[s].time += l.time_spent;
        });
        const total = logs.length;
        const correct = logs.filter((l) => l.is_correct).length;
        const totalTime = logs.reduce((s, l) => s + l.time_spent, 0);
        const subjectStats = Object.entries(subjectMap).map(([subject, v]) => ({
            subject,
            total: v.total,
            correct: v.correct,
            wrong: v.total - v.correct,
            accuracy: Math.round((v.correct / v.total) * 100),
            avg_time: Math.round(v.time / v.total),
        }));
        const sorted = [...subjectStats].sort((a, b) => a.accuracy - b.accuracy);
        const wrongTotal = total - correct;
        return {
            user_id: -1,
            has_data: true,
            total_solved: total,
            overall_accuracy: Math.round((correct / total) * 100),
            overall_avg_time: Math.round(totalTime / total),
            subject_stats: subjectStats,
            weak_subjects: sorted.slice(0, 2).filter((s) => s.accuracy < 70),
            strong_subjects: sorted.slice(-2).filter((s) => s.accuracy >= 70).reverse(),
            trend: [],
            repeated_wrong: [],
            wrong_distribution: sorted
                .filter((s) => s.wrong > 0)
                .map((s) => ({
                    subject: s.subject,
                    wrong_count: s.wrong,
                    percentage: wrongTotal > 0 ? Math.round((s.wrong / wrongTotal) * 100) : 0,
                })),
        };
    };

    // 풀이 로그 분석만
    const handleAnalyze = async () => {
        if (isGuest) {
            const logs = loadGuestLogs() || [];
            if (logs.length === 0) {
                setError("가상 모의고사(랜덤/선택)를 먼저 풀어주세요. 풀이 기록은 브라우저에만 임시 저장됩니다.");
                return;
            }
            const a = computeGuestAnalysis(logs);
            if (a) {
                setAnalysis(a);
                setActiveTab("analysis");
            }
            return;
        }
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
    const [generateElapsed, setGenerateElapsed] = useState(0);

    const handleGenerate = async () => {
        setIsGenerating(true);
        setError(null);
        setGenerateElapsed(0);

        // 경과 시간 표시 타이머
        const timerStart = Date.now();
        const timer = setInterval(() => {
            setGenerateElapsed(Math.floor((Date.now() - timerStart) / 1000));
        }, 1000);

        try {
            let body: Record<string, unknown>;
            if (isGuest) {
                let guestProfile: Record<string, unknown> = {};
                try {
                    const pr = localStorage.getItem(GUEST_PROFILE_KEY);
                    if (pr) guestProfile = JSON.parse(pr);
                } catch {
                    /* ignore */
                }
                body = {
                    action: "generate_guest",
                    question: "내 풀이 데이터를 분석해서 최적의 학습 계획을 세워줘",
                    guest_profile: guestProfile,
                    guest_logs: loadGuestLogs() || [],
                };
            } else {
                body = {
                    action: "generate",
                    user_id: parseInt(userId),
                    question: "내 풀이 데이터를 분석해서 최적의 학습 계획을 세워줘",
                };
            }

            const res = await fetch("/api/study-plan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const data = await res.json();
            if (data.success) {
                if (data.analysis) setAnalysis(data.analysis);
                const plan = data.study_plan || data.plan;
                if (plan?.plan_json) {
                    setPlanJson(sanitizeDeep(plan.plan_json));
                } else if (data.plan_json) {
                    setPlanJson(sanitizeDeep(data.plan_json));
                }
                setGenerationMethod(data.generation_method || "template");
                const sources = data.rag_sources
                    || plan?.plan_json?.rag_sources
                    || data.plan_json?.rag_sources
                    || [];
                setRagSources(sanitizeDeep(sources));
                setActiveTab("plan");
            } else {
                setError(data.error || "학습 계획 생성에 실패했습니다.");
            }
        } catch (e) {
            const elapsed = Math.floor((Date.now() - timerStart) / 1000);
            if (elapsed >= 290) {
                setError("AI 생성 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.");
            } else {
                setError("서버에 연결할 수 없습니다. 백엔드 서버 상태를 확인해주세요.");
            }
        } finally {
            clearInterval(timer);
            setIsGenerating(false);
            setGenerateElapsed(0);
        }
    };

    // 기존 학습 계획 조회
    const handleLoadPlan = async () => {
        if (isGuest) {
            setError("게스트 모드에서는 서버에 저장된 학습 계획이 없습니다. AI 플랜 생성으로만 확인할 수 있습니다.");
            return;
        }
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
                    setPlanJson(sanitizeDeep(plan.plan_json));
                    setGenerationMethod(plan.plan_json.generated_by || "unknown");
                    setRagSources(sanitizeDeep(plan.plan_json.rag_sources || []));
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
                    {loggedInUser && (
                        <button type="button" onClick={handleLogout} className="logout-link">로그아웃</button>
                    )}
                    {isGuest && (
                        <a href="/login" className="logout-link" style={{ color: "rgba(251,191,36,0.8)" }}>로그인</a>
                    )}
                </div>
            </header>

            {isGuest && (
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "10px 32px",
                        fontSize: "0.78rem",
                        color: "rgba(251,191,36,0.8)",
                        background: "rgba(251,191,36,0.06)",
                        borderBottom: "1px solid rgba(251,191,36,0.1)",
                    }}
                >
                    게스트(임시) — 풀이·학습계획은 DB에 저장되지 않으며, 브라우저를 닫으면 사라질 수 있습니다.
                    <a href="/user" style={{ marginLeft: "auto", color: "rgba(251,191,36,1)", fontWeight: 600 }}>학습 프로필 →</a>
                </div>
            )}

            {/* 사용자 선택 + 액션 버튼 */}
            <div className="action-bar">
                <div className="user-input-group">
                    <label className="input-label">
                        {isGuest
                            ? "임시 게스트"
                            : loggedInUser?.display_name
                                ? `${loggedInUser.display_name} 님`
                                : userLoading ? "로딩 중..." : "사용자 ID"}
                    </label>
                    {isGuest ? (
                        <span className="user-input" style={{ display: "inline-block", border: "none", opacity: 0.85 }}>
                            —
                        </span>
                    ) : (
                        <input
                            type="number"
                            value={userId}
                            onChange={(e) => setUserId(e.target.value)}
                            className="user-input"
                            min="1"
                            readOnly={!!loggedInUser?.id}
                            style={loggedInUser?.id ? { opacity: 0.7, cursor: "default" } : {}}
                        />
                    )}
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
                        disabled={isAnalyzing || isGenerating || isLoadingPlan || isGuest}
                        className="btn btn-load-plan"
                        title={isGuest ? "게스트는 서버 저장 계획이 없습니다" : undefined}
                    >
                        {isLoadingPlan ? "조회 중..." : "📋 학습 계획"}
                    </button>
                <span className="generate-wrapper">
                    <button
                        onClick={handleGenerate}
                        disabled={
                            isAnalyzing || isGenerating || isLoadingPlan ||
                            !isProfileSet || !analysis?.has_data
                        }
                        className={`btn btn-generate${
                            !isProfileSet || !analysis?.has_data ? " btn-generate-locked" : ""
                        }`}
                    >
                        {isGenerating
                            ? `생성 중... ${generateElapsed > 0 ? `(${generateElapsed}초)` : ""}`
                            : "🤖 AI 플랜 생성"}
                    </button>
                    {(!isProfileSet || !analysis?.has_data) && (
                        <span className="generate-tooltip">
                            {isGuest
                                ? "사용자 정보(임시)에서 학습 프로필을 저장한 뒤, 모의고사를 풀고 「풀이 분석」을 눌러주세요."
                                : "사용자 정보를 설정하고, 가상모의고사를 통한 풀이 분석을 진행해주세요. 정교한 학습 계획을 생성할 수 있습니다."}
                        </span>
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
                    <div className="badge-row">
                        <div className="method-badge">
                            {generationMethod === "exaone" ? "🤖 EXAONE 생성" : "📋 템플릿 생성"}
                        </div>
                        {planJson.user_profile_applied && (
                            <div className="method-badge profile-badge">
                                👤 사용자 프로필 반영
                            </div>
                        )}
                    </div>

                    {/* 사용자 프로필 반영 정보 */}
                    {planJson.user_profile_applied && planJson.user_profile_summary && (
                        <div className="card section-card profile-summary-card">
                            <h3 className="section-title">👤 반영된 사용자 프로필</h3>
                            <div className="profile-chips">
                                {planJson.user_profile_summary.target_position && (
                                    <span className="profile-chip chip-position">
                                        🎯 {planJson.user_profile_summary.target_position}
                                    </span>
                                )}
                                {planJson.user_profile_summary.is_first_timer !== undefined && (
                                    <span className="profile-chip chip-timer">
                                        {planJson.user_profile_summary.is_first_timer ? "🆕 초시생" : "🔄 재시생"}
                                    </span>
                                )}
                                {planJson.user_profile_summary.employment_status && (
                                    <span className="profile-chip chip-status">
                                        💼 {planJson.user_profile_summary.employment_status}
                                    </span>
                                )}
                                {planJson.user_profile_summary.age && (
                                    <span className="profile-chip chip-age">
                                        🎂 {planJson.user_profile_summary.age}세
                                    </span>
                                )}
                                {planJson.user_profile_summary.daily_study_time && (
                                    <span className="profile-chip chip-time">
                                        ⏰ 일 {(planJson.user_profile_summary.daily_study_time / 60).toFixed(1)}시간
                                    </span>
                                )}
                                {planJson.user_profile_summary.study_duration && (
                                    <span className="profile-chip chip-date">
                                        📅 목표 {planJson.user_profile_summary.study_duration}
                                    </span>
                                )}
                            </div>
                            {(planJson.user_profile_summary.weak_subjects?.length ?? 0) > 0 && (
                                <div className="profile-subjects-row">
                                    <span className="profile-subjects-label">⚠️ 취약 과목:</span>
                                    {planJson.user_profile_summary.weak_subjects?.map((s) => (
                                        <span key={s} className="profile-chip chip-weak">{s}</span>
                                    ))}
                                </div>
                            )}
                            {(planJson.user_profile_summary.strong_subjects?.length ?? 0) > 0 && (
                                <div className="profile-subjects-row">
                                    <span className="profile-subjects-label">✅ 강점 과목:</span>
                                    {planJson.user_profile_summary.strong_subjects?.map((s) => (
                                        <span key={s} className="profile-chip chip-strong">{s}</span>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* 요약 */}
                    {planJson.summary && (
                        <div className="card section-card">
                            <h3 className="section-title">📝 분석 요약</h3>
                            <p className="plan-summary">{planJson.summary}</p>
                        </div>
                    )}

                    {/* 매칭된 합격 수기 분석 */}
                    {planJson.matched_stories_analysis && (
                        <div className="card section-card matched-stories-card">
                            <h3 className="section-title">🔍 유사 환경 합격자 분석</h3>
                            <p className="matched-stories-text">{planJson.matched_stories_analysis}</p>
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

                    {/* 과목별 학습 전략 (합격 수기 기반) */}
                    {planJson.subject_plans && planJson.subject_plans.length > 0 && (
                        <div className="card section-card">
                            <h3 className="section-title">📚 과목별 학습 전략</h3>
                            <div className="subject-plans-list">
                                {dedupeSubjectPlans(planJson.subject_plans).map((sp) => (
                                    <details key={sp.subject} className="subject-plan-item">
                                        <summary className="subject-plan-summary">
                                            <span className="subject-plan-name">{sp.subject}</span>
                                            {sp.priority && (
                                                <span className={`subject-priority priority-${sp.priority === "높음" ? "high" : sp.priority === "유지" ? "keep" : "normal"}`}>
                                                    {sp.priority}
                                                </span>
                                            )}
                                            {sp.current_level && (
                                                <span className="subject-level">{sp.current_level}</span>
                                            )}
                                            {sp.weekly_hours && (
                                                <span className="subject-hours">주 {sp.weekly_hours}h</span>
                                            )}
                                        </summary>
                                        <div className="subject-plan-detail">
                                            {sp.strategy && (
                                                <div className="subject-detail-row">
                                                    <span className="detail-label">📖 전략:</span>
                                                    <span className="detail-value">{sp.strategy}</span>
                                                </div>
                                            )}
                                            {sp.recommended_materials && (
                                                <div className="subject-detail-row">
                                                    <span className="detail-label">📝 추천:</span>
                                                    <span className="detail-value">{sp.recommended_materials}</span>
                                                </div>
                                            )}
                                        </div>
                                    </details>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 일일 학습 루틴 */}
                    {planJson.daily_routine && (
                        <div className="card section-card">
                            <h3 className="section-title">⏰ 추천 일일 루틴</h3>
                            {planJson.daily_routine.description && (
                                <p className="routine-description">{planJson.daily_routine.description}</p>
                            )}
                            <div className="routine-timeline">
                                {planJson.daily_routine.morning && (
                                    <div className="routine-block routine-morning">
                                        <span className="routine-emoji">🌅</span>
                                        <div>
                                            <div className="routine-label">오전</div>
                                            <div className="routine-content">{planJson.daily_routine.morning}</div>
                                        </div>
                                    </div>
                                )}
                                {planJson.daily_routine.afternoon && (
                                    <div className="routine-block routine-afternoon">
                                        <span className="routine-emoji">☀️</span>
                                        <div>
                                            <div className="routine-label">오후</div>
                                            <div className="routine-content">{planJson.daily_routine.afternoon}</div>
                                        </div>
                                    </div>
                                )}
                                {planJson.daily_routine.evening && (
                                    <div className="routine-block routine-evening">
                                        <span className="routine-emoji">🌙</span>
                                        <div>
                                            <div className="routine-label">저녁</div>
                                            <div className="routine-content">{planJson.daily_routine.evening}</div>
                                        </div>
                                    </div>
                                )}
                                {planJson.daily_routine.review && (
                                    <div className="routine-block routine-review">
                                        <span className="routine-emoji">📋</span>
                                        <div>
                                            <div className="routine-label">복습/정리</div>
                                            <div className="routine-content">{planJson.daily_routine.review}</div>
                                        </div>
                                    </div>
                                )}
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

                    {/* 합격자 학습법 (수기 인용) */}
                    {planJson.study_methods && planJson.study_methods.length > 0 && (
                        <div className="card section-card">
                            <h3 className="section-title">🎓 합격자 학습법</h3>
                            <div className="study-methods-list">
                                {planJson.study_methods.map((sm, i) => (
                                    <div key={i} className="study-method-item">
                                        <div className="method-title">{sm.method}</div>
                                        <div className="method-desc">{sm.description}</div>
                                        {sm.source_story && (
                                            <span className="method-source">📖 {sm.source_story}</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 어려움 극복 방안 */}
                    {planJson.difficulty_management && planJson.difficulty_management.length > 0 && (
                        <div className="card section-card">
                            <h3 className="section-title">💪 어려움 극복 방안</h3>
                            <ul className="difficulty-list">
                                {planJson.difficulty_management.map((d, i) => (
                                    <li key={i} className="difficulty-item">{d}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* 핵심 합격 전략 */}
                    {planJson.key_strategies && planJson.key_strategies.length > 0 && (
                        <div className="card section-card">
                            <h3 className="section-title">🎯 핵심 합격 전략</h3>
                            <ol className="strategy-list">
                                {planJson.key_strategies.map((s, i) => (
                                    <li key={i} className="strategy-item">{s}</li>
                                ))}
                            </ol>
                        </div>
                    )}

                    {/* 학습 조언 */}
                    {planJson.specific_advice && planJson.specific_advice.length > 0 && (
                        <div className="card section-card">
                            <h3 className="section-title">💡 맞춤 학습 조언</h3>
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

                    {/* 참고한 합격 수기 출처 */}
                    {ragSources.length > 0 && (
                        <div className="card section-card rag-sources-card">
                            <h3 className="section-title">📖 참고한 합격 수기</h3>
                            <p className="rag-sources-desc">
                                사용자와 유사한 환경의 합격자 {ragSources.length}명의 수기를 분석하여 학습 계획을 생성했습니다.
                            </p>
                            <div className="rag-sources-list">
                                {ragSources.map((src) => (
                                    <details key={src.id} className="rag-source-item">
                                        <summary className="rag-source-summary">
                                            <span className="rag-source-rank">#{src.rank}</span>
                                            <span className="rag-source-question">{src.title}</span>
                                            <span className="rag-source-intent story-badge">
                                                {src.source_name === "gongdanki" ? "공단기" : src.source_name === "megagong" ? "메가공" : src.source_name || "합격수기"}
                                            </span>
                                            <span className="rag-source-similarity">
                                                유사도 {(src.similarity * 100).toFixed(0)}%
                                                {(src.profile_bonus ?? 0) > 0 && (
                                                    <span className="profile-bonus-badge">
                                                        +환경매칭
                                                    </span>
                                                )}
                                            </span>
                                        </summary>
                                        <div className="rag-source-detail">
                                            {/* 환경 매칭 이유 */}
                                            {src.match_reasons && src.match_reasons.length > 0 && (
                                                <div className="rag-source-meta match-reasons">
                                                    <span className="rag-meta-label">🤝 매칭 이유:</span>
                                                    <span className="rag-meta-value">
                                                        {src.match_reasons.map((r, i) => (
                                                            <span key={i} className="match-reason-chip">{r}</span>
                                                        ))}
                                                    </span>
                                                </div>
                                            )}
                                            {/* 수험 정보 */}
                                            {src.study_info && (
                                                <div className="rag-source-meta">
                                                    <span className="rag-meta-label">📊 수험 정보:</span>
                                                    <span className="rag-meta-value">{src.study_info}</span>
                                                </div>
                                            )}
                                            {/* 학습법이 있는 과목 */}
                                            {src.method_subjects && src.method_subjects.length > 0 && (
                                                <div className="rag-source-meta">
                                                    <span className="rag-meta-label">📚 학습법 과목:</span>
                                                    <span className="rag-meta-value">{src.method_subjects.join(", ")}</span>
                                                </div>
                                            )}
                                            {/* 과목별 학습법 미리보기 */}
                                            {src.subject_methods_preview && Object.keys(src.subject_methods_preview).length > 0 && (
                                                <div className="rag-source-section">
                                                    <span className="rag-detail-label">📖 과목별 학습법</span>
                                                    {dedupeMethodPreviewEntries(src.subject_methods_preview).map(([subj, method]) => (
                                                        <div key={subj} className="method-preview-item">
                                                            <strong>{subj}:</strong> {method}
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                            {/* 일일 학습 계획 미리보기 */}
                                            {src.context_preview && (
                                                <div className="rag-source-section">
                                                    <span className="rag-detail-label">📅 일일 학습 계획</span>
                                                    <p className="rag-detail-text">{src.context_preview}</p>
                                                </div>
                                            )}
                                            {/* 핵심 전략 미리보기 */}
                                            {src.key_points_preview && (
                                                <div className="rag-source-section">
                                                    <span className="rag-detail-label">🎯 핵심 전략</span>
                                                    <p className="rag-detail-text">{src.key_points_preview}</p>
                                                </div>
                                            )}
                                            {/* 어려움 극복 미리보기 */}
                                            {src.difficulties_preview && (
                                                <div className="rag-source-section">
                                                    <span className="rag-detail-label">💪 어려움 극복</span>
                                                    <p className="rag-detail-text">{src.difficulties_preview}</p>
                                                </div>
                                            )}
                                            {/* 출처 링크 */}
                                            {src.source_url && (
                                                <div className="rag-source-link">
                                                    <a href={src.source_url} target="_blank" rel="noopener noreferrer">
                                                        🔗 원문 보기 ({src.source_name === "gongdanki" ? "공단기" : src.source_name === "megagong" ? "메가공" : "출처"})
                                                    </a>
                                                </div>
                                            )}
                                        </div>
                                    </details>
                                ))}
                            </div>
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
                .btn-generate-locked {
                    opacity: 0.4;
                    cursor: not-allowed !important;
                    filter: grayscale(0.4);
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
                    white-space: normal;
                    width: max-content;
                    max-width: 320px;
                    text-align: center;
                    padding: 10px 16px;
                    border-radius: 8px;
                    background: rgba(20,20,20,0.97);
                    border: 1px solid rgba(168,85,247,0.2);
                    color: rgba(255,255,255,0.75);
                    font-size: 0.72rem;
                    line-height: 1.5;
                    opacity: 0;
                    visibility: hidden;
                    transition: all 0.2s ease;
                    pointer-events: none;
                    z-index: 10;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                }
                .generate-tooltip::after {
                    content: "";
                    position: absolute;
                    top: 100%;
                    left: 50%;
                    transform: translateX(-50%);
                    border: 5px solid transparent;
                    border-top-color: rgba(168,85,247,0.2);
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
                .badge-row {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                    margin-bottom: 16px;
                }
                .method-badge {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 6px;
                    background: rgba(168,85,247,0.1);
                    border: 1px solid rgba(168,85,247,0.2);
                    color: #c084fc;
                    font-size: 0.72rem;
                }
                .profile-badge {
                    background: rgba(59,130,246,0.1);
                    border-color: rgba(59,130,246,0.2);
                    color: #60a5fa;
                }

                /* ── 사용자 프로필 요약 카드 ── */
                .profile-summary-card {
                    background: rgba(59,130,246,0.03);
                    border-color: rgba(59,130,246,0.1);
                }
                .profile-chips {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                    margin-bottom: 10px;
                }
                .profile-chip {
                    padding: 4px 10px;
                    border-radius: 14px;
                    font-size: 0.72rem;
                    font-weight: 500;
                    background: rgba(255,255,255,0.04);
                    border: 1px solid rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.6);
                }
                .chip-position {
                    background: rgba(168,85,247,0.1);
                    border-color: rgba(168,85,247,0.2);
                    color: #c084fc;
                }
                .chip-timer {
                    background: rgba(34,197,94,0.1);
                    border-color: rgba(34,197,94,0.2);
                    color: #4ade80;
                }
                .chip-status {
                    background: rgba(251,146,60,0.1);
                    border-color: rgba(251,146,60,0.2);
                    color: #fb923c;
                }
                .chip-weak {
                    background: rgba(239,68,68,0.1);
                    border-color: rgba(239,68,68,0.2);
                    color: #f87171;
                }
                .chip-strong {
                    background: rgba(34,197,94,0.1);
                    border-color: rgba(34,197,94,0.2);
                    color: #4ade80;
                }
                .profile-subjects-row {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 6px;
                    align-items: center;
                    margin-top: 6px;
                }
                .profile-subjects-label {
                    font-size: 0.72rem;
                    color: rgba(255,255,255,0.4);
                    font-weight: 500;
                    margin-right: 2px;
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

                /* ── 유사 환경 합격자 분석 ── */
                .matched-stories-card {
                    border-left: 3px solid rgba(34,197,94,0.4);
                }
                .matched-stories-text {
                    font-size: 0.85rem;
                    color: rgba(255,255,255,0.65);
                    line-height: 1.7;
                    margin: 0;
                }

                /* ── 과목별 학습 전략 ── */
                .subject-plans-list {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }
                .subject-plan-item {
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.05);
                    border-radius: 8px;
                    overflow: hidden;
                    transition: border-color 0.2s;
                }
                .subject-plan-item[open] {
                    border-color: rgba(59,130,246,0.2);
                }
                .subject-plan-summary {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 10px 14px;
                    cursor: pointer;
                    font-size: 0.82rem;
                    color: rgba(255,255,255,0.7);
                    list-style: none;
                    transition: background 0.15s;
                }
                .subject-plan-summary:hover {
                    background: rgba(255,255,255,0.03);
                }
                .subject-plan-summary::-webkit-details-marker { display: none; }
                .subject-plan-name {
                    font-weight: 600;
                    color: rgba(255,255,255,0.85);
                    min-width: 60px;
                }
                .subject-priority {
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 0.65rem;
                    font-weight: 700;
                    flex-shrink: 0;
                }
                .priority-high {
                    background: rgba(239,68,68,0.15);
                    color: #f87171;
                }
                .priority-normal {
                    background: rgba(250,204,21,0.15);
                    color: #facc15;
                }
                .priority-keep {
                    background: rgba(74,222,128,0.15);
                    color: #4ade80;
                }
                .subject-level {
                    font-size: 0.7rem;
                    color: rgba(255,255,255,0.4);
                    flex: 1;
                }
                .subject-hours {
                    font-size: 0.68rem;
                    color: rgba(255,255,255,0.3);
                    flex-shrink: 0;
                }
                .subject-plan-detail {
                    padding: 0 14px 14px;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                .subject-detail-row {
                    display: flex;
                    gap: 8px;
                    font-size: 0.78rem;
                    line-height: 1.6;
                }
                .detail-label {
                    color: rgba(255,255,255,0.5);
                    font-weight: 600;
                    flex-shrink: 0;
                    min-width: 55px;
                }
                .detail-value {
                    color: rgba(255,255,255,0.6);
                    word-break: keep-all;
                }

                /* ── 일일 루틴 ── */
                .routine-description {
                    font-size: 0.8rem;
                    color: rgba(255,255,255,0.5);
                    line-height: 1.6;
                    margin: 0 0 14px 0;
                }
                .routine-timeline {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                .routine-block {
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                    padding: 12px 14px;
                    border-radius: 8px;
                    background: rgba(255,255,255,0.02);
                    border-left: 3px solid transparent;
                }
                .routine-morning { border-left-color: rgba(251,191,36,0.5); }
                .routine-afternoon { border-left-color: rgba(59,130,246,0.5); }
                .routine-evening { border-left-color: rgba(168,85,247,0.5); }
                .routine-review { border-left-color: rgba(34,197,94,0.5); }
                .routine-emoji {
                    font-size: 1.2rem;
                    flex-shrink: 0;
                    margin-top: 2px;
                }
                .routine-label {
                    font-size: 0.72rem;
                    color: rgba(255,255,255,0.4);
                    font-weight: 600;
                    margin-bottom: 2px;
                }
                .routine-content {
                    font-size: 0.82rem;
                    color: rgba(255,255,255,0.65);
                    line-height: 1.5;
                }

                /* ── 합격자 학습법 ── */
                .study-methods-list {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                .study-method-item {
                    padding: 12px 14px;
                    background: rgba(255,255,255,0.02);
                    border-radius: 8px;
                    border-left: 3px solid rgba(59,130,246,0.3);
                }
                .method-title {
                    font-size: 0.82rem;
                    font-weight: 600;
                    color: rgba(255,255,255,0.75);
                    margin-bottom: 6px;
                }
                .method-desc {
                    font-size: 0.78rem;
                    color: rgba(255,255,255,0.55);
                    line-height: 1.6;
                    word-break: keep-all;
                }
                .method-source {
                    display: inline-block;
                    margin-top: 6px;
                    font-size: 0.68rem;
                    color: rgba(168,85,247,0.7);
                }

                /* ── 어려움 극복 ── */
                .difficulty-list {
                    list-style: none;
                    padding: 0;
                    margin: 0;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                .difficulty-item {
                    font-size: 0.82rem;
                    color: rgba(255,255,255,0.6);
                    line-height: 1.6;
                    padding: 10px 14px;
                    background: rgba(251,191,36,0.04);
                    border-radius: 8px;
                    border-left: 3px solid rgba(251,191,36,0.3);
                    word-break: keep-all;
                }

                /* ── 핵심 합격 전략 ── */
                .strategy-list {
                    list-style-position: inside;
                    padding: 0;
                    margin: 0;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                .strategy-item {
                    font-size: 0.82rem;
                    color: rgba(255,255,255,0.65);
                    line-height: 1.6;
                    padding: 10px 14px;
                    background: rgba(34,197,94,0.04);
                    border-radius: 8px;
                    border-left: 3px solid rgba(34,197,94,0.3);
                    word-break: keep-all;
                }

                /* ── 프로필 매칭 보너스 ── */
                .profile-bonus-badge {
                    display: inline-block;
                    margin-left: 4px;
                    padding: 1px 5px;
                    background: rgba(34,197,94,0.2);
                    color: #4ade80;
                    border-radius: 3px;
                    font-size: 0.6rem;
                    font-weight: 600;
                }
                .match-reasons {
                    background: rgba(34,197,94,0.08) !important;
                }
                .match-reason-chip {
                    display: inline-block;
                    padding: 2px 8px;
                    background: rgba(34,197,94,0.15);
                    color: #4ade80;
                    border-radius: 4px;
                    font-size: 0.65rem;
                    margin-right: 4px;
                }
                .method-preview-item {
                    font-size: 0.75rem;
                    color: rgba(255,255,255,0.5);
                    line-height: 1.6;
                    padding: 4px 0;
                    border-bottom: 1px solid rgba(255,255,255,0.03);
                    word-break: keep-all;
                }
                .method-preview-item:last-child {
                    border-bottom: none;
                }
                .method-preview-item strong {
                    color: rgba(255,255,255,0.65);
                }

                /* ── 합격 수기 출처 ── */
                .rag-sources-card { margin-top: 16px; }
                .rag-sources-desc {
                    font-size: 0.75rem;
                    color: rgba(255,255,255,0.3);
                    margin: 0 0 14px 0;
                    line-height: 1.4;
                }
                .rag-sources-list {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                .rag-source-item {
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.05);
                    border-radius: 8px;
                    overflow: hidden;
                    transition: border-color 0.2s;
                }
                .rag-source-item[open] {
                    border-color: rgba(168,85,247,0.2);
                }
                .rag-source-summary {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 10px 14px;
                    cursor: pointer;
                    font-size: 0.78rem;
                    color: rgba(255,255,255,0.6);
                    list-style: none;
                    transition: background 0.15s;
                }
                .rag-source-summary:hover {
                    background: rgba(255,255,255,0.03);
                }
                .rag-source-summary::-webkit-details-marker { display: none; }
                .rag-source-rank {
                    background: rgba(168,85,247,0.15);
                    color: #c084fc;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 0.68rem;
                    font-weight: 700;
                    flex-shrink: 0;
                }
                .rag-source-question {
                    flex: 1;
                    overflow: hidden;
                    white-space: nowrap;
                    text-overflow: ellipsis;
                    color: rgba(255,255,255,0.7);
                }
                .rag-source-intent {
                    background: rgba(59,130,246,0.1);
                    color: #60a5fa;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 0.65rem;
                    flex-shrink: 0;
                }
                .rag-source-intent.story-badge {
                    background: rgba(34,197,94,0.15);
                    color: #4ade80;
                }
                .rag-story-count {
                    color: #4ade80;
                    font-weight: 600;
                }
                .rag-source-similarity {
                    color: rgba(255,255,255,0.3);
                    font-size: 0.68rem;
                    flex-shrink: 0;
                }
                .rag-source-detail {
                    padding: 0 14px 14px;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                .rag-source-section {
                    background: rgba(255,255,255,0.02);
                    border-radius: 6px;
                    padding: 10px 12px;
                }
                .rag-detail-label {
                    display: block;
                    font-size: 0.68rem;
                    color: rgba(255,255,255,0.4);
                    margin-bottom: 6px;
                    font-weight: 600;
                }
                .rag-detail-text {
                    font-size: 0.75rem;
                    color: rgba(255,255,255,0.45);
                    line-height: 1.6;
                    margin: 0;
                    word-break: keep-all;
                }
                .rag-source-meta {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 0.72rem;
                    padding: 6px 12px;
                    background: rgba(34,197,94,0.06);
                    border-radius: 6px;
                }
                .rag-meta-label {
                    color: rgba(255,255,255,0.5);
                    font-weight: 600;
                    flex-shrink: 0;
                }
                .rag-meta-value {
                    color: rgba(255,255,255,0.6);
                }
                .rag-source-link {
                    padding: 4px 12px;
                }
                .rag-source-link a {
                    font-size: 0.7rem;
                    color: #60a5fa;
                    text-decoration: none;
                    opacity: 0.7;
                    transition: opacity 0.2s;
                }
                .rag-source-link a:hover {
                    opacity: 1;
                    text-decoration: underline;
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
                    .rag-source-summary {
                        flex-wrap: wrap;
                        gap: 6px;
                        padding: 8px 10px;
                        font-size: 0.72rem;
                    }
                    .rag-source-question {
                        width: 100%;
                        order: 3;
                        white-space: normal;
                    }
                    .rag-source-detail {
                        padding: 0 10px 10px;
                    }
                    .rag-detail-text {
                        font-size: 0.7rem;
                    }
                }
            `}</style>
        </div>
    );
}

