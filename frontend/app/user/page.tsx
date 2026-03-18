"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { logout, API_BASE_URL, authFetch, startSocialLink, storeLinkedProviders } from "@/lib/auth-api";
import { useUser, LinkedAccount } from "@/lib/hooks/useUser";

// ============================================================================
// 상수 정의
// ============================================================================

const POSITIONS = [
    "일반행정", "세무", "관세", "통계", "교육행정", "회계",
    "교정", "보호", "검찰", "출입국관리", "철도경찰",
    "사회복지", "직업상담", "기술직", "기타",
];

const SUBJECTS = [
    "국어", "영어", "한국사", "행정법총론", "행정학개론",
    "사회", "과학", "수학", "세법개론", "회계학",
    "교육학개론", "사회복지학개론", "교정학개론",
    "형사소송법", "헌법",
];

const EMPLOYMENT_OPTIONS = [
    { value: "EMPLOYED", label: "재직 중" },
    { value: "UNEMPLOYED", label: "전업 수험생" },
    { value: "STUDENT", label: "학생" },
    { value: "SELF_EMPLOYED", label: "자영업" },
    { value: "OTHER", label: "기타" },
];

// ============================================================================
// 타입
// ============================================================================

type UserProfile = {
    id: number;
    display_name: string;
    age: number | null;
    employment_status: string | null;
    base_score: number | null;
    daily_study_time: number | null;
    study_duration: string | null;
    is_first_timer: boolean | null;
    target_position: string | null;
    weak_subjects: string | null;
    strong_subjects: string | null;
    registration_date: string | null;
    last_login: string | null;
    provider: string | null;
};

// ============================================================================
// 게스트 프로필 localStorage 키
// ============================================================================

const GUEST_PROFILE_KEY = "gja_guest_profile";

function loadGuestProfile(): Partial<UserProfile> {
    if (typeof window === "undefined") return {};
    try {
        const raw = localStorage.getItem(GUEST_PROFILE_KEY);
        if (raw) return JSON.parse(raw);
    } catch { /* 무시 */ }
    return {};
}

function saveGuestProfile(data: Partial<UserProfile>): void {
    try {
        localStorage.setItem(GUEST_PROFILE_KEY, JSON.stringify(data));
    } catch { /* 무시 */ }
}

// ============================================================================
// 메인 컴포넌트
// ============================================================================

function UserProfilePageContent() {
    const { user: loggedInUser, loading: userLoading } = useUser();
    const isGuest = !userLoading && !loggedInUser;

    // 프로필 데이터
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [profileLoading, setProfileLoading] = useState(true);

    // 편집 모드
    const [isEditing, setIsEditing] = useState(false);

    // 편집 폼 상태
    const [formAge, setFormAge] = useState<string>("");
    const [formEmployment, setFormEmployment] = useState<string>("");
    const [formFirstTimer, setFormFirstTimer] = useState<string>("");
    const [formStudyDuration, setFormStudyDuration] = useState<string>("");
    const [formTargetPosition, setFormTargetPosition] = useState<string>("");
    const [formWeakSubjects, setFormWeakSubjects] = useState<string[]>([]);
    const [formStrongSubjects, setFormStrongSubjects] = useState<string[]>([]);

    // 저장 상태
    const [isSaving, setIsSaving] = useState(false);
    const [saveMessage, setSaveMessage] = useState<string | null>(null);

    // 계정 연동 상태
    const [linkMessage, setLinkMessage] = useState<string | null>(null);
    const [isLinking, setIsLinking] = useState(false);
    const searchParams = useSearchParams();

    // 프로필 불러오기
    const fetchProfile = async () => {
        if (!loggedInUser?.id) return;
        setProfileLoading(true);
        try {
            const res = await authFetch(`${API_BASE_URL}/api/v1/admin/users/${loggedInUser.id}`);
            if (res.ok) {
                const data = await res.json();
                if (data.success && data.user) {
                    setProfile(data.user);
                    syncFormFromProfile(data.user);
                }
            }
        } catch (e) {
            console.warn("[UserProfile] 프로필 불러오기 실패:", e);
        } finally {
            setProfileLoading(false);
        }
    };

    // 프로필 → 폼 동기화
    const syncFormFromProfile = (p: UserProfile) => {
        setFormAge(p.age != null ? String(p.age) : "");
        setFormEmployment(p.employment_status || "");
        setFormFirstTimer(p.is_first_timer === true ? "true" : p.is_first_timer === false ? "false" : "");
        setFormStudyDuration(p.study_duration || "");
        setFormTargetPosition(p.target_position || "");
        setFormWeakSubjects(p.weak_subjects ? p.weak_subjects.split(",").map(s => s.trim()).filter(Boolean) : []);
        setFormStrongSubjects(p.strong_subjects ? p.strong_subjects.split(",").map(s => s.trim()).filter(Boolean) : []);
    };

    useEffect(() => {
        if (userLoading) return;
        if (loggedInUser?.id) {
            fetchProfile();
        } else {
            // 게스트: localStorage에서 프로필 로드
            const guestData = loadGuestProfile();
            if (Object.keys(guestData).length > 0) {
                setFormAge(guestData.age != null ? String(guestData.age) : "");
                setFormEmployment(guestData.employment_status || "");
                setFormFirstTimer(guestData.is_first_timer === true ? "true" : guestData.is_first_timer === false ? "false" : "");
                setFormStudyDuration(guestData.study_duration || "");
                setFormTargetPosition(guestData.target_position || "");
                setFormWeakSubjects(guestData.weak_subjects ? guestData.weak_subjects.split(",").map(s => s.trim()).filter(Boolean) : []);
                setFormStrongSubjects(guestData.strong_subjects ? guestData.strong_subjects.split(",").map(s => s.trim()).filter(Boolean) : []);
            }
            setIsEditing(false);
            setProfileLoading(false);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [userLoading, loggedInUser?.id]);

    // URL 쿼리에서 연동 결과 확인
    useEffect(() => {
        const linked = searchParams.get("linked");
        const linkError = searchParams.get("link_error");

        if (linked) {
            const providerLabel = linked === "kakao" ? "카카오" : linked === "naver" ? "네이버" : linked === "google" ? "구글" : linked;
            setLinkMessage(`✅ ${providerLabel} 계정이 성공적으로 연동되었습니다!`);
            // localStorage에 새로 연동된 프로바이더 추가
            try {
                const raw = localStorage.getItem("gja_linked_providers");
                const current: string[] = raw ? JSON.parse(raw) : [];
                if (!current.includes(linked)) {
                    current.push(linked);
                    storeLinkedProviders(current);
                }
            } catch { /* 무시 */ }
            // URL에서 쿼리 파라미터 제거
            window.history.replaceState({}, "", "/user");
        } else if (linkError) {
            const errorMessages: Record<string, string> = {
                auth: "인증이 만료되었습니다. 다시 로그인해주세요.",
                user_not_found: "현재 사용자를 찾을 수 없습니다.",
                already_linked: "이미 다른 사용자에게 연동된 계정입니다.",
                server_error: "서버 오류가 발생했습니다. 다시 시도해주세요.",
            };
            setLinkMessage(`❌ ${errorMessages[linkError] || "계정 연동에 실패했습니다."}`);
            window.history.replaceState({}, "", "/user");
        }
    }, [searchParams]);

    // 자동 메시지 사라짐
    useEffect(() => {
        if (!linkMessage) return;
        const t = setTimeout(() => setLinkMessage(null), 5000);
        return () => clearTimeout(t);
    }, [linkMessage]);

    // 소셜 계정 연동 시작
    const handleLinkProvider = async (provider: string) => {
        setIsLinking(true);
        setLinkMessage(null);
        try {
            await startSocialLink(provider);
        } catch (err) {
            console.error("[UserProfile] 계정 연동 시작 실패:", err);
            setLinkMessage("❌ 계정 연동을 시작할 수 없습니다.");
            setIsLinking(false);
        }
    };

    // 과목 토글
    const toggleSubject = (subject: string, list: string[], setList: (v: string[]) => void) => {
        if (list.includes(subject)) {
            setList(list.filter(s => s !== subject));
        } else {
            setList([...list, subject]);
        }
    };

    // 편집 취소
    const handleCancelEdit = () => {
        if (profile) syncFormFromProfile(profile);
        setIsEditing(false);
        setSaveMessage(null);
    };

    // 초기화 (모든 필드 비우기)
    const handleReset = () => {
        setFormAge("");
        setFormEmployment("");
        setFormFirstTimer("");
        setFormStudyDuration("");
        setFormTargetPosition("");
        setFormWeakSubjects([]);
        setFormStrongSubjects([]);
        setSaveMessage(null);
    };

    // 저장
    const handleSave = async () => {
        setIsSaving(true);
        setSaveMessage(null);

        // 게스트: localStorage에 저장
        if (!loggedInUser?.id) {
            try {
                const guestData: Partial<UserProfile> = {
                    age: formAge ? parseInt(formAge) : null,
                    employment_status: formEmployment || null,
                    is_first_timer: formFirstTimer === "true" ? true : formFirstTimer === "false" ? false : null,
                    study_duration: formStudyDuration || null,
                    target_position: formTargetPosition || null,
                    weak_subjects: formWeakSubjects.length > 0 ? formWeakSubjects.join(",") : null,
                    strong_subjects: formStrongSubjects.length > 0 ? formStrongSubjects.join(",") : null,
                };
                saveGuestProfile(guestData);
                setSaveMessage("임시 저장 완료! (로그인 시 DB에 저장됩니다)");
                setIsEditing(false);
            } finally {
                setIsSaving(false);
            }
            return;
        }

        try {
            // 항상 모든 필드를 전송 — 빈 값은 null 로 보내 DB 에서 클리어
            const body: Record<string, unknown> = {
                age: formAge ? parseInt(formAge) : null,
                employment_status: formEmployment || null,
                is_first_timer: formFirstTimer === "true" ? true : formFirstTimer === "false" ? false : null,
                study_duration: formStudyDuration || null,
                target_position: formTargetPosition || null,
                weak_subjects: formWeakSubjects.length > 0 ? formWeakSubjects.join(",") : null,
                strong_subjects: formStrongSubjects.length > 0 ? formStrongSubjects.join(",") : null,
            };

            const res = await authFetch(`${API_BASE_URL}/api/v1/admin/users/${loggedInUser.id}/profile`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });

            if (res.ok) {
                const data = await res.json();
                if (data.success && data.user) {
                    setProfile(data.user);
                    syncFormFromProfile(data.user);
                    setSaveMessage("저장 완료!");
                    setIsEditing(false);
                } else {
                    setSaveMessage("저장 실패: " + (data.detail || "알 수 없는 오류"));
                }
            } else {
                setSaveMessage("저장 실패: 서버 오류");
            }
        } catch (e) {
            console.error("[UserProfile] 저장 실패:", e);
            setSaveMessage("저장 중 오류가 발생했습니다.");
        } finally {
            setIsSaving(false);
        }
    };

    const handleLogout = () => {
        logout(); // 백엔드 리다이렉트로 쿠키 삭제 + /login 이동
    };

    // 프로바이더 뱃지
    const getProviderBadge = (provider: string | null | undefined) => {
        switch (provider) {
            case "kakao": return { emoji: "🟡", label: "카카오", cls: "provider-kakao" };
            case "naver": return { emoji: "🟢", label: "네이버", cls: "provider-naver" };
            case "google": return { emoji: "🔵", label: "구글", cls: "provider-google" };
            default: return null;
        }
    };

    const providerInfo = getProviderBadge(profile?.provider || loggedInUser?.provider);

    return (
        <div className="page-container">
            {/* 헤더 */}
            <header className="page-header">
                <div className="header-left">
                    <a href="/chat" className="back-link">← 채팅</a>
                    <h1 className="page-title">사용자 정보</h1>
                </div>
                <div className="header-right">
                    <a href="/" className="home-link">홈</a>
                    <button onClick={handleLogout} className="logout-link">로그아웃</button>
                </div>
            </header>

            {/* 메인 컨텐츠 */}
            <div className="content-area">
                {(userLoading || profileLoading) ? (
                    <div className="loading-state">
                        <div className="loading-spinner" />
                        <p>사용자 정보를 불러오는 중...</p>
                    </div>
                ) : isGuest ? (
                    /* ── 게스트 모드: 임시 프로필 입력 폼 ── */
                    <>
                        <div className="guest-notice-card">
                            <span className="guest-notice-icon">👤</span>
                            <div className="guest-notice-body">
                                <p className="guest-notice-title">게스트 모드</p>
                                <p className="guest-notice-desc">
                                    프로필을 입력하면 브라우저에 임시 저장됩니다. 로그인하면 DB에 영구 저장되며 AI 플랜 정확도가 높아집니다.
                                </p>
                            </div>
                            <a href="/login" className="guest-login-btn">로그인하기 →</a>
                        </div>
                        {/* 게스트 프로필 편집 폼 (항상 편집 모드) */}
                        <div className="card">
                            <div className="card-header">
                                <h3 className="card-title">📋 학습 프로필 (임시)</h3>
                            </div>
                            {saveMessage && (
                                <div className={`save-message ${saveMessage.includes("완료") ? "success" : "error"}`}>
                                    {saveMessage}
                                </div>
                            )}
                            <div className="form-grid">
                                <div className="form-field">
                                    <label className="form-label">나이</label>
                                    <input type="number" className="form-input" value={formAge} onChange={e => setFormAge(e.target.value)} placeholder="예) 25" min="18" max="60" />
                                </div>
                                <div className="form-field">
                                    <label className="form-label">직장 여부</label>
                                    <select className="form-select" value={formEmployment} onChange={e => setFormEmployment(e.target.value)}>
                                        <option value="">선택</option>
                                        {EMPLOYMENT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                                    </select>
                                </div>
                                <div className="form-field">
                                    <label className="form-label">초시 여부</label>
                                    <select className="form-select" value={formFirstTimer} onChange={e => setFormFirstTimer(e.target.value)}>
                                        <option value="">선택</option>
                                        <option value="true">초시생</option>
                                        <option value="false">재시생</option>
                                    </select>
                                </div>
                                <div className="form-field">
                                    <label className="form-label">합격 목표 기간</label>
                                    <input type="text" className="form-input" value={formStudyDuration} onChange={e => setFormStudyDuration(e.target.value)} placeholder="예) 6개월, 1년" />
                                </div>
                                <div className="form-field full-width">
                                    <label className="form-label">목표 직렬</label>
                                    <div className="chips-grid">
                                        {POSITIONS.map(p => (
                                            <button key={p} type="button" className={`chip ${formTargetPosition === p ? "chip-active" : ""}`} onClick={() => setFormTargetPosition(formTargetPosition === p ? "" : p)}>{p}</button>
                                        ))}
                                    </div>
                                </div>
                                <div className="form-field full-width">
                                    <label className="form-label">취약 과목 (복수 선택)</label>
                                    <div className="chips-grid">
                                        {SUBJECTS.map(s => (
                                            <button key={s} type="button" className={`chip chip-weak ${formWeakSubjects.includes(s) ? "chip-active" : ""}`} onClick={() => toggleSubject(s, formWeakSubjects, setFormWeakSubjects)}>{s}</button>
                                        ))}
                                    </div>
                                </div>
                                <div className="form-field full-width">
                                    <label className="form-label">강점 과목 (복수 선택)</label>
                                    <div className="chips-grid">
                                        {SUBJECTS.map(s => (
                                            <button key={s} type="button" className={`chip chip-strong ${formStrongSubjects.includes(s) ? "chip-active" : ""}`} onClick={() => toggleSubject(s, formStrongSubjects, setFormStrongSubjects)}>{s}</button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                            <div className="form-actions">
                                <button onClick={handleReset} className="btn-reset" disabled={isSaving}>초기화</button>
                                <button onClick={handleSave} className="btn-save" disabled={isSaving}>{isSaving ? "저장 중..." : "임시 저장"}</button>
                            </div>
                        </div>
                    </>
                ) : (
                    <>
                        {/* ── 프로필 카드 ── */}
                        <div className="card profile-card">
                            <div className="profile-top">
                                <div className="avatar">
                                    <span className="avatar-text">
                                        {loggedInUser?.display_name?.charAt(0) || "?"}
                                    </span>
                                </div>
                                <div className="profile-info">
                                    <h2 className="profile-name">
                                        {loggedInUser?.display_name || "이름 없음"}
                                    </h2>
                                    <div className="profile-meta">
                                        {providerInfo && (
                                            <span className={`provider-badge ${providerInfo.cls}`}>
                                                {providerInfo.emoji} {providerInfo.label}
                                            </span>
                                        )}
                                        <span className="id-badge">ID: {loggedInUser?.id}</span>
                                    </div>
                                </div>
                            </div>
                            {profile?.registration_date && (
                                <p className="join-date">
                                    가입일: {new Date(profile.registration_date).toLocaleDateString("ko-KR")}
                                    {profile.last_login && (
                                        <> · 마지막 로그인: {new Date(profile.last_login).toLocaleDateString("ko-KR")}</>
                                    )}
                                </p>
                            )}
                        </div>

                        {/* ── 소셜 계정 연동 카드 ── */}
                        <div className="card">
                            <div className="card-header">
                                <h3 className="card-title">🔗 소셜 계정 연동</h3>
                            </div>

                            {/* 연동 결과 메시지 */}
                            {linkMessage && (
                                <div className={`save-message ${linkMessage.startsWith("✅") ? "success" : "error"}`}>
                                    {linkMessage}
                                </div>
                            )}

                            {/* 연동된 계정 목록 */}
                            <div className="linked-accounts-list">
                                {(["kakao", "naver", "google"] as const).map((provider) => {
                                    const badge = getProviderBadge(provider);
                                    const linked = loggedInUser?.linked_accounts?.find(
                                        (acc) => acc.provider === provider
                                    );

                                    return (
                                        <div key={provider} className="linked-account-item">
                                            <span className={`provider-badge ${badge?.cls || ""}`}>
                                                {badge?.emoji || "⚪"} {badge?.label || provider}
                                            </span>

                                            {linked ? (
                                                <>
                                                    {linked.email && (
                                                        <span className="linked-email">{linked.email}</span>
                                                    )}
                                                    <span className="linked-status linked-status-ok">연동됨</span>
                                                    {linked.linked_at && (
                                                        <span className="linked-date">
                                                            {new Date(linked.linked_at).toLocaleDateString("ko-KR")}
                                                        </span>
                                                    )}
                                                </>
                                            ) : (
                                                <>
                                                    <span className="linked-status linked-status-no">미연동</span>
                                                    <button
                                                        className="link-btn"
                                                        onClick={() => handleLinkProvider(provider)}
                                                        disabled={isLinking}
                                                    >
                                                        {isLinking ? "연동 중..." : "연동하기"}
                                                    </button>
                                                </>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* ── 학습 프로필 카드 ── */}
                        <div className="card">
                            <div className="card-header">
                                <h3 className="card-title">📋 학습 프로필</h3>
                                {!isEditing ? (
                                    <button className="edit-btn" onClick={() => setIsEditing(true)}>수정</button>
                                ) : (
                                    <div className="edit-actions">
                                        <button className="reset-btn" onClick={handleReset}>초기화</button>
                                        <button className="cancel-btn" onClick={handleCancelEdit}>취소</button>
                                        <button className="save-btn" onClick={handleSave} disabled={isSaving}>
                                            {isSaving ? "저장 중..." : "저장"}
                                        </button>
                                    </div>
                                )}
                            </div>

                            {saveMessage && (
                                <div className={`save-message ${saveMessage.includes("완료") ? "success" : "error"}`}>
                                    {saveMessage}
                                </div>
                            )}

                            <div className="form-grid">
                                {/* 나이 */}
                                <div className="form-group">
                                    <label className="form-label">나이</label>
                                    {isEditing ? (
                                        <input
                                            type="number"
                                            className="form-input"
                                            value={formAge}
                                            onChange={(e) => setFormAge(e.target.value)}
                                            placeholder="나이 입력"
                                            min={15}
                                            max={80}
                                        />
                                    ) : (
                                        <span className="form-value">{profile?.age ? `${profile.age}세` : "미설정"}</span>
                                    )}
                                </div>

                                {/* 직장 여부 */}
                                <div className="form-group">
                                    <label className="form-label">직장 여부</label>
                                    {isEditing ? (
                                        <select
                                            className="form-select"
                                            value={formEmployment}
                                            onChange={(e) => setFormEmployment(e.target.value)}
                                        >
                                            <option value="">선택</option>
                                            {EMPLOYMENT_OPTIONS.map(opt => (
                                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                                            ))}
                                        </select>
                                    ) : (
                                        <span className="form-value">
                                            {profile?.employment_status
                                                ? EMPLOYMENT_OPTIONS.find(o => o.value === profile.employment_status)?.label || profile.employment_status
                                                : "미설정"}
                                        </span>
                                    )}
                                </div>

                                {/* 초시 여부 */}
                                <div className="form-group">
                                    <label className="form-label">초시 여부</label>
                                    {isEditing ? (
                                        <select
                                            className="form-select"
                                            value={formFirstTimer}
                                            onChange={(e) => setFormFirstTimer(e.target.value)}
                                        >
                                            <option value="">선택</option>
                                            <option value="true">초시 (첫 응시)</option>
                                            <option value="false">재시 (재응시)</option>
                                        </select>
                                    ) : (
                                        <span className="form-value">
                                            {profile?.is_first_timer === true ? "초시 (첫 응시)"
                                                : profile?.is_first_timer === false ? "재시 (재응시)"
                                                    : "미설정"}
                                        </span>
                                    )}
                                </div>

                                {/* 목표 기간 */}
                                <div className="form-group">
                                    <label className="form-label">목표 기간 (총 수험기간)</label>
                                    {isEditing ? (
                                        <select
                                            className="form-select"
                                            value={formStudyDuration}
                                            onChange={(e) => setFormStudyDuration(e.target.value)}
                                        >
                                            <option value="">선택</option>
                                            <option value="3개월 이내">3개월 이내</option>
                                            <option value="6개월">6개월</option>
                                            <option value="9개월">9개월</option>
                                            <option value="1년">1년</option>
                                            <option value="1년 6개월">1년 6개월</option>
                                            <option value="2년">2년</option>
                                            <option value="2년 이상">2년 이상</option>
                                            <option value="3년 이상">3년 이상</option>
                                        </select>
                                    ) : (
                                        <span className="form-value">{profile?.study_duration || "미설정"}</span>
                                    )}
                                </div>

                                {/* 목표 직렬 */}
                                <div className="form-group full-width">
                                    <label className="form-label">목표 직렬</label>
                                    {isEditing ? (
                                        <div className="chip-grid">
                                            {POSITIONS.map(pos => (
                                                <button
                                                    key={pos}
                                                    className={`chip ${formTargetPosition === pos ? "chip-active" : ""}`}
                                                    onClick={() => setFormTargetPosition(formTargetPosition === pos ? "" : pos)}
                                                >
                                                    {pos}
                                                </button>
                                            ))}
                                        </div>
                                    ) : (
                                        <span className="form-value">{profile?.target_position || "미설정"}</span>
                                    )}
                                </div>

                                {/* 취약 과목 */}
                                <div className="form-group full-width">
                                    <label className="form-label">취약 과목</label>
                                    {isEditing ? (
                                        <div className="chip-grid">
                                            {SUBJECTS.map(subj => (
                                                <button
                                                    key={subj}
                                                    className={`chip chip-weak ${formWeakSubjects.includes(subj) ? "chip-active" : ""}`}
                                                    onClick={() => toggleSubject(subj, formWeakSubjects, setFormWeakSubjects)}
                                                >
                                                    {subj}
                                                </button>
                                            ))}
                                        </div>
                                    ) : (
                                        <span className="form-value">
                                            {profile?.weak_subjects
                                                ? profile.weak_subjects.split(",").map(s => s.trim()).join(", ")
                                                : "미설정"}
                                        </span>
                                    )}
                                </div>

                                {/* 강점 과목 */}
                                <div className="form-group full-width">
                                    <label className="form-label">강점 과목</label>
                                    {isEditing ? (
                                        <div className="chip-grid">
                                            {SUBJECTS.map(subj => (
                                                <button
                                                    key={subj}
                                                    className={`chip chip-strong ${formStrongSubjects.includes(subj) ? "chip-active" : ""}`}
                                                    onClick={() => toggleSubject(subj, formStrongSubjects, setFormStrongSubjects)}
                                                >
                                                    {subj}
                                                </button>
                                            ))}
                                        </div>
                                    ) : (
                                        <span className="form-value">
                                            {profile?.strong_subjects
                                                ? profile.strong_subjects.split(",").map(s => s.trim()).join(", ")
                                                : "미설정"}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>

            <style jsx>{`
                .page-container {
                    min-height: 100vh;
                    background: #000;
                    color: #fff;
                    font-family: "Gothic A1", "Noto Sans KR", "Malgun Gothic", "맑은 고딕", sans-serif;
                }

                /* ── 헤더 ── */
                .page-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 16px 24px;
                    border-bottom: 1px solid rgba(255,255,255,0.04);
                    background: rgba(0,0,0,0.6);
                    backdrop-filter: blur(12px);
                    position: sticky;
                    top: 0;
                    z-index: 10;
                }
                .header-left {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                }
                .back-link {
                    color: rgba(255,255,255,0.4);
                    text-decoration: none;
                    font-size: 0.82rem;
                    transition: color 0.2s;
                }
                .back-link:hover { color: rgba(255,255,255,0.8); }
                .page-title {
                    font-size: 1rem;
                    font-weight: 600;
                    color: rgba(255,255,255,0.9);
                    margin: 0;
                }
                .header-right {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                .home-link {
                    color: rgba(255,255,255,0.3);
                    text-decoration: none;
                    font-size: 0.75rem;
                    transition: color 0.2s;
                }
                .home-link:hover { color: rgba(255,255,255,0.7); }
                .logout-link {
                    background: none;
                    border: none;
                    color: rgba(255,100,100,0.5);
                    font-size: 0.75rem;
                    cursor: pointer;
                    font-family: inherit;
                    transition: color 0.2s;
                }
                .logout-link:hover { color: rgba(255,100,100,0.9); }

                /* ── 컨텐츠 ── */
                .content-area {
                    max-width: 640px;
                    margin: 0 auto;
                    padding: 24px 16px 60px;
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }

                /* ── 로딩 ── */
                .loading-state {
                    text-align: center;
                    padding: 80px 0;
                    color: rgba(255,255,255,0.3);
                    font-size: 0.85rem;
                }
                .loading-spinner {
                    width: 28px;
                    height: 28px;
                    border: 2px solid rgba(255,255,255,0.1);
                    border-top-color: rgba(255,255,255,0.4);
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                    margin: 0 auto 16px;
                }
                @keyframes spin { to { transform: rotate(360deg); } }

                .guest-notice-card {
                    display: flex;
                    align-items: center;
                    gap: 14px;
                    padding: 16px 20px;
                    background: rgba(251,191,36,0.06);
                    border: 1px solid rgba(251,191,36,0.12);
                    border-radius: 12px;
                    margin-bottom: 16px;
                }
                .guest-notice-icon { font-size: 1.5rem; flex-shrink: 0; }
                .guest-notice-body { flex: 1; }
                .guest-notice-title {
                    font-size: 0.85rem;
                    font-weight: 600;
                    color: rgba(251,191,36,0.9);
                    margin: 0 0 4px;
                }
                .guest-notice-desc {
                    font-size: 0.75rem;
                    color: rgba(255,255,255,0.4);
                    margin: 0;
                    line-height: 1.5;
                }
                .guest-login-btn {
                    flex-shrink: 0;
                    padding: 8px 16px;
                    background: rgba(251,191,36,0.1);
                    border: 1px solid rgba(251,191,36,0.25);
                    border-radius: 8px;
                    color: rgba(251,191,36,0.9);
                    font-size: 0.78rem;
                    font-weight: 600;
                    text-decoration: none;
                    transition: background 0.2s;
                }
                .guest-login-btn:hover { background: rgba(251,191,36,0.18); }

                .empty-state {
                    text-align: center;
                    padding: 80px 0;
                    color: rgba(255,255,255,0.4);
                    font-size: 0.85rem;
                }
                .login-btn {
                    display: inline-block;
                    margin-top: 16px;
                    padding: 8px 24px;
                    background: rgba(255,255,255,0.08);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 8px;
                    color: rgba(255,255,255,0.7);
                    text-decoration: none;
                    font-size: 0.82rem;
                    transition: all 0.2s;
                }
                .login-btn:hover {
                    background: rgba(255,255,255,0.12);
                    color: #fff;
                }

                /* ── 카드 ── */
                .card {
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 12px;
                    padding: 20px;
                }

                /* ── 프로필 카드 ── */
                .profile-card {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }
                .profile-top {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                }
                .avatar {
                    width: 56px;
                    height: 56px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
                    border: 1px solid rgba(255,255,255,0.1);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-shrink: 0;
                }
                .avatar-text {
                    font-size: 1.4rem;
                    font-weight: 700;
                    color: rgba(255,255,255,0.7);
                }
                .profile-info {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }
                .profile-name {
                    font-size: 1.15rem;
                    font-weight: 600;
                    color: rgba(255,255,255,0.9);
                    margin: 0;
                }
                .profile-meta {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    flex-wrap: wrap;
                }
                .provider-badge {
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 0.68rem;
                    font-weight: 600;
                }
                .provider-kakao {
                    background: rgba(254,229,0,0.1);
                    color: rgba(254,229,0,0.85);
                    border: 1px solid rgba(254,229,0,0.12);
                }
                .provider-naver {
                    background: rgba(3,199,90,0.1);
                    color: rgba(3,199,90,0.85);
                    border: 1px solid rgba(3,199,90,0.12);
                }
                .provider-google {
                    background: rgba(66,133,244,0.1);
                    color: rgba(66,133,244,0.85);
                    border: 1px solid rgba(66,133,244,0.12);
                }
                /* ── 연동 소셜 계정 ── */
                .linked-accounts-list {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                .linked-account-item {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 10px 14px;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 10px;
                }
                .linked-email {
                    font-size: 0.78rem;
                    color: rgba(255,255,255,0.5);
                }
                .linked-date {
                    font-size: 0.7rem;
                    color: rgba(255,255,255,0.3);
                }
                .linked-status {
                    font-size: 0.7rem;
                    font-weight: 500;
                    padding: 2px 8px;
                    border-radius: 8px;
                    margin-left: auto;
                }
                .linked-status-ok {
                    color: rgba(74,222,128,0.9);
                    background: rgba(34,197,94,0.1);
                    border: 1px solid rgba(34,197,94,0.15);
                }
                .linked-status-no {
                    color: rgba(255,255,255,0.3);
                    background: rgba(255,255,255,0.03);
                    border: 1px solid rgba(255,255,255,0.06);
                }
                .link-btn {
                    background: rgba(59,130,246,0.12);
                    border: 1px solid rgba(59,130,246,0.25);
                    color: rgba(96,165,250,0.9);
                    font-size: 0.7rem;
                    padding: 4px 14px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-family: inherit;
                    font-weight: 500;
                    transition: all 0.2s;
                    white-space: nowrap;
                }
                .link-btn:hover {
                    background: rgba(59,130,246,0.2);
                    border-color: rgba(59,130,246,0.4);
                }
                .link-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .id-badge {
                    font-size: 0.68rem;
                    color: rgba(255,255,255,0.25);
                    background: rgba(255,255,255,0.04);
                    padding: 2px 8px;
                    border-radius: 10px;
                }
                .join-date {
                    font-size: 0.72rem;
                    color: rgba(255,255,255,0.25);
                    margin: 0;
                    padding-top: 4px;
                    border-top: 1px solid rgba(255,255,255,0.04);
                }

                /* ── 카드 헤더 ── */
                .card-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 16px;
                }
                .card-title {
                    font-size: 0.95rem;
                    font-weight: 600;
                    color: rgba(255,255,255,0.85);
                    margin: 0;
                }
                .edit-btn {
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.5);
                    font-size: 0.72rem;
                    padding: 5px 14px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-family: inherit;
                    transition: all 0.2s;
                }
                .edit-btn:hover {
                    background: rgba(255,255,255,0.1);
                    color: rgba(255,255,255,0.8);
                }
                .edit-actions {
                    display: flex;
                    gap: 6px;
                }
                .reset-btn {
                    background: transparent;
                    border: 1px solid rgba(239,68,68,0.15);
                    color: rgba(252,165,165,0.6);
                    font-size: 0.72rem;
                    padding: 5px 14px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-family: inherit;
                    transition: all 0.2s;
                }
                .reset-btn:hover {
                    background: rgba(239,68,68,0.08);
                    color: rgba(252,165,165,0.9);
                    border-color: rgba(239,68,68,0.25);
                }
                .cancel-btn {
                    background: transparent;
                    border: 1px solid rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.4);
                    font-size: 0.72rem;
                    padding: 5px 14px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-family: inherit;
                    transition: all 0.2s;
                }
                .cancel-btn:hover {
                    color: rgba(255,255,255,0.7);
                }
                .save-btn {
                    background: rgba(59,130,246,0.15);
                    border: 1px solid rgba(59,130,246,0.25);
                    color: rgba(96,165,250,0.9);
                    font-size: 0.72rem;
                    padding: 5px 14px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-family: inherit;
                    font-weight: 500;
                    transition: all 0.2s;
                }
                .save-btn:hover {
                    background: rgba(59,130,246,0.25);
                }
                .save-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                /* ── 저장 메시지 ── */
                .save-message {
                    font-size: 0.75rem;
                    padding: 8px 12px;
                    border-radius: 6px;
                    margin-bottom: 12px;
                }
                .save-message.success {
                    background: rgba(34,197,94,0.1);
                    color: rgba(74,222,128,0.9);
                    border: 1px solid rgba(34,197,94,0.15);
                }
                .save-message.error {
                    background: rgba(239,68,68,0.1);
                    color: rgba(252,165,165,0.9);
                    border: 1px solid rgba(239,68,68,0.15);
                }

                /* ── 폼 그리드 ── */
                .form-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 16px;
                }
                .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }
                .form-group.full-width {
                    grid-column: 1 / -1;
                }
                .form-label {
                    font-size: 0.72rem;
                    color: rgba(255,255,255,0.35);
                    font-weight: 500;
                    letter-spacing: 0.02em;
                }
                .form-value {
                    font-size: 0.82rem;
                    color: rgba(255,255,255,0.7);
                    padding: 8px 0;
                }
                .form-input {
                    background: rgba(255,255,255,0.04);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 0.82rem;
                    color: rgba(255,255,255,0.85);
                    font-family: inherit;
                    outline: none;
                    transition: border-color 0.2s;
                }
                .form-input:focus {
                    border-color: rgba(255,255,255,0.2);
                }
                .form-input::placeholder {
                    color: rgba(255,255,255,0.2);
                }
                .form-select {
                    background: rgba(255,255,255,0.04);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 0.82rem;
                    color: rgba(255,255,255,0.85);
                    font-family: inherit;
                    outline: none;
                    cursor: pointer;
                    transition: border-color 0.2s;
                    appearance: none;
                    -webkit-appearance: none;
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='rgba(255,255,255,0.3)' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
                    background-repeat: no-repeat;
                    background-position: right 10px center;
                    padding-right: 30px;
                }
                .form-select:focus {
                    border-color: rgba(255,255,255,0.2);
                }
                .form-select option {
                    background: #111;
                    color: #fff;
                }

                /* ── 칩 (과목/직렬 선택) ── */
                .chip-grid {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 6px;
                }
                .chip {
                    padding: 5px 12px;
                    border-radius: 16px;
                    font-size: 0.72rem;
                    font-family: inherit;
                    cursor: pointer;
                    border: 1px solid rgba(255,255,255,0.08);
                    background: rgba(255,255,255,0.03);
                    color: rgba(255,255,255,0.45);
                    transition: all 0.2s;
                    font-weight: 500;
                }
                .chip:hover {
                    background: rgba(255,255,255,0.06);
                    color: rgba(255,255,255,0.7);
                }
                .chip.chip-active {
                    background: rgba(59,130,246,0.15);
                    border-color: rgba(59,130,246,0.3);
                    color: rgba(96,165,250,0.95);
                }
                .chip.chip-weak.chip-active {
                    background: rgba(239,68,68,0.12);
                    border-color: rgba(239,68,68,0.25);
                    color: rgba(252,165,165,0.95);
                }
                .chip.chip-strong.chip-active {
                    background: rgba(34,197,94,0.12);
                    border-color: rgba(34,197,94,0.25);
                    color: rgba(74,222,128,0.95);
                }

                /* ── 모바일 반응형 ── */
                @media (max-width: 640px) {
                    .page-header {
                        padding: 12px 14px;
                    }
                    .page-title {
                        font-size: 0.9rem;
                    }
                    .content-area {
                        padding: 16px 12px 40px;
                    }
                    .form-grid {
                        grid-template-columns: 1fr;
                    }
                    .profile-name {
                        font-size: 1rem;
                    }
                    .avatar {
                        width: 48px;
                        height: 48px;
                    }
                    .avatar-text {
                        font-size: 1.2rem;
                    }
                }

                @media (max-width: 360px) {
                    .card {
                        padding: 14px;
                    }
                    .chip {
                        padding: 4px 10px;
                        font-size: 0.68rem;
                    }
                }
            `}</style>
        </div>
    );
}

export default function UserProfilePage() {
    return (
        <Suspense fallback={<div style={{ padding: 24, color: "#fff" }}>로딩 중...</div>}>
            <UserProfilePageContent />
        </Suspense>
    );
}

