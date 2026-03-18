"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { logout } from "@/lib/auth-api";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";

/* ─── 타입 ─── */
type KoELECTRAMeta = {
    gateway?: string | null;
    confidence?: number | null;
    method?: string | null;
};
type ChatMessage = {
    role: "bot" | "user";
    text: string;
    mode?: string;
    retrieved_docs?: string[] | null;
    koelectra?: KoELECTRAMeta | null;
};

/* ─── 유틸 ─── */
function generateSessionId() {
    return "sess_" + crypto.randomUUID().replace(/-/g, "").slice(0, 16);
}
const STORAGE_KEY_MESSAGES = "chat_messages";
const STORAGE_KEY_THREAD_ID = "chat_thread_id";

const WELCOME_MESSAGE: ChatMessage = {
    role: "bot",
    text: "안녕하세요! 공잘알 AI 멘토입니다.\n\n공무원 시험 준비에 대해 무엇이든 물어보세요.\n합격 수기 4,910건의 데이터를 기반으로 맞춤 조언을 드립니다.\n\n💡 예시 질문:\n• 노베이스 1년 일행직 어떻게 준비해?\n• 행정법 교재 추천해줘\n• 단기 합격 학습 계획 짜줘\n• 독학 vs 학원 어떤게 나을까?",
};

function loadMessagesFromStorage(): ChatMessage[] {
    if (typeof window === "undefined") return [WELCOME_MESSAGE];
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY_MESSAGES);
        if (raw) {
            const parsed = JSON.parse(raw) as ChatMessage[];
            if (Array.isArray(parsed) && parsed.length > 0) return parsed;
        }
    } catch { /* ignore */ }
    return [WELCOME_MESSAGE];
}
function loadThreadIdFromStorage(): string {
    if (typeof window === "undefined") return generateSessionId();
    try {
        const saved = sessionStorage.getItem(STORAGE_KEY_THREAD_ID);
        if (saved) return saved;
    } catch { /* ignore */ }
    const newId = generateSessionId();
    sessionStorage.setItem(STORAGE_KEY_THREAD_ID, newId);
    return newId;
}

/* ─── SVG 아이콘 ─── */
const IcMenu = () => (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
        <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
    </svg>
);
const IcPencil = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
);
const IcHome = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
);
const IcUpload = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 16 12 12 8 16" /><line x1="12" y1="12" x2="12" y2="21" />
        <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
);
const IcExam = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
    </svg>
);
const IcPlan = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
);
const IcUser = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
    </svg>
);
const IcSettings = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
        <circle cx="12" cy="12" r="3" />
    </svg>
);
const IcInfo = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" />
    </svg>
);
const IcLogout = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
        <polyline points="16 17 21 12 16 7" />
        <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
);
const IcSend = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" />
    </svg>
);

/* ─── 사이드바 아이템 컴포넌트 ─── */
function SideItem({
    icon, label, expanded, onClick, href, danger = false,
}: {
    icon: React.ReactNode; label: string; expanded: boolean;
    onClick?: () => void; href?: string; danger?: boolean;
}) {
    const [hovered, setHovered] = useState(false);

    const baseStyle: React.CSSProperties = {
        display: "flex",
        flexDirection: "row",
        flexWrap: "nowrap",
        alignItems: "center",
        gap: "14px",
        width: "100%",
        padding: expanded ? "12px 16px" : "12px 0",
        justifyContent: expanded ? "flex-start" : "center",
        border: "none",
        borderRadius: "8px",
        background: hovered
            ? danger ? "rgba(255,80,80,0.07)" : "rgba(255,255,255,0.06)"
            : "transparent",
        color: danger
            ? hovered ? "rgba(255,100,100,0.9)" : "rgba(255,100,100,0.5)"
            : hovered ? "rgba(255,255,255,0.88)" : "rgba(255,255,255,0.45)",
        fontSize: "1.03rem",
        fontFamily: "inherit",
        letterSpacing: "0.02em",
        lineHeight: 1.3,
        textAlign: "left",
        textDecoration: "none",
        cursor: "pointer",
        whiteSpace: "nowrap",
        wordBreak: "keep-all",
        overflow: "hidden",
        flexShrink: 0,
        transition: "background 0.15s ease, color 0.15s ease",
        boxSizing: "border-box",
        position: "relative",
    };

    const iconStyle: React.CSSProperties = {
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: "22px",
        height: "22px",
    };

    const labelStyle: React.CSSProperties = {
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        wordBreak: "keep-all",
        flex: 1,
        minWidth: 0,
        display: "block",
    };

    const content = (
        <>
            <span style={iconStyle}>{icon}</span>
            {expanded && <span style={labelStyle}>{label}</span>}
            {!expanded && hovered && (
                <span style={{
                    position: "absolute",
                    left: "calc(100% + 10px)",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "rgba(20,20,20,0.98)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    color: "rgba(255,255,255,0.85)",
                    fontSize: "0.8rem",
                    padding: "6px 12px",
                    borderRadius: "6px",
                    whiteSpace: "nowrap",
                    zIndex: 400,
                    pointerEvents: "none",
                }}>
                    {label}
                </span>
            )}
        </>
    );

    if (href) {
        return (
            <a
                href={href}
                style={baseStyle}
                onMouseEnter={() => setHovered(true)}
                onMouseLeave={() => setHovered(false)}
            >
                {content}
            </a>
        );
    }
    return (
        <button
            style={baseStyle}
            onClick={onClick}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
        >
            {content}
        </button>
    );
}

/* ════════════════════════════════════════
   메인 컴포넌트
════════════════════════════════════════ */
export default function ChatbotUI() {
    const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isInfoOpen, setIsInfoOpen] = useState(false);
    const [isNewChatHover, setIsNewChatHover] = useState(false);

    /* 사이드바 상태 */
    const [sideExpanded, setSideExpanded] = useState(true);   // 데스크톱: 펼침/접힘
    const [mobileOpen, setMobileOpen] = useState(false);       // 모바일: 오버레이 오픈
    const [isMobile, setIsMobile] = useState(false);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const threadIdRef = useRef<string>("");

    /* 반응형 감지 */
    useEffect(() => {
        const check = () => setIsMobile(window.innerWidth < 768);
        check();
        window.addEventListener("resize", check);
        return () => window.removeEventListener("resize", check);
    }, []);

    /* 마운트 시 복원 */
    useEffect(() => {
        setMessages(loadMessagesFromStorage());
        threadIdRef.current = loadThreadIdFromStorage();
    }, []);

    /* 메시지 저장 */
    useEffect(() => {
        if (messages.length <= 1 && messages[0]?.text === WELCOME_MESSAGE.text) return;
        try { sessionStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(messages)); } catch { /* ignore */ }
    }, [messages]);

    /* 스크롤 */
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    /* 새 대화 */
    const handleNewChat = useCallback(() => {
        const newId = generateSessionId();
        threadIdRef.current = newId;
        sessionStorage.setItem(STORAGE_KEY_THREAD_ID, newId);
        const fresh: ChatMessage[] = [WELCOME_MESSAGE];
        setMessages(fresh);
        sessionStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(fresh));
        if (isMobile) setMobileOpen(false);
    }, [isMobile]);

    /* 로그아웃 */
    const handleLogout = () => {
        if (isMobile) setMobileOpen(false);
        logout();
    };

    /* 메시지 전송 */
    const sendMessage = async () => {
        const question = input.trim();
        if (!question || isLoading) return;
        setMessages((prev) => [...prev, { role: "user", text: question }]);
        setInput("");
        setIsLoading(true);
        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question, mode: "rag_local", thread_id: threadIdRef.current }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || `HTTP ${res.status}`);
            }
            const data = await res.json();
            setMessages((prev) => [
                ...prev,
                {
                    role: "bot",
                    text: typeof data?.answer === "string" ? data.answer : data?.error || "응답을 생성하지 못했습니다.",
                    mode: data?.mode,
                    retrieved_docs: data?.retrieved_docs,
                    koelectra: data?.koelectra ?? null,
                },
            ]);
        } catch {
            setMessages((prev) => [...prev, { role: "bot", text: "오류가 발생했습니다. 잠시 후 다시 시도해 주세요." }]);
        } finally {
            setIsLoading(false);
        }
    };

    /* 사이드바 펼침 여부 (실제 렌더링 기준) */
    const showExpanded = isMobile ? true : sideExpanded;
    const sidebarVisible = isMobile ? mobileOpen : true;

    /* ── 사이드바 렌더 ── */
    const sidebar = (
        <aside className={`sidebar ${!isMobile && !sideExpanded ? "sidebar-collapsed" : ""} ${isMobile ? "sidebar-mobile" : ""}`}>
            {/* 상단: 토글 + 로고 */}
            <div className="side-top">
                <button
                    className="side-toggle"
                    onClick={() => isMobile ? setMobileOpen(false) : setSideExpanded((p) => !p)}
                    aria-label="메뉴 접기"
                >
                    <IcMenu />
                </button>
                {showExpanded && (
                    <a href="/" className="side-logo">공잘알</a>
                )}
            </div>

            {/* 새 대화 버튼 */}
            <button
                onClick={handleNewChat}
                title={!showExpanded ? "새 대화" : undefined}
                onMouseEnter={() => setIsNewChatHover(true)}
                onMouseLeave={() => setIsNewChatHover(false)}
                style={{
                    display: "flex",
                    flexDirection: "row",
                    flexWrap: "nowrap",
                    alignItems: "center",
                    justifyContent: showExpanded ? "flex-start" : "center",
                    gap: showExpanded ? "14px" : 0,
                    width: "100%",
                    padding: showExpanded ? "13px 16px" : "12px",
                    border: "1px solid",
                    borderColor: isNewChatHover ? "rgba(255,255,255,0.13)" : "rgba(255,255,255,0.08)",
                    borderRadius: "9px",
                    background: isNewChatHover ? "rgba(255,255,255,0.05)" : "transparent",
                    color: isNewChatHover ? "rgba(255,255,255,0.88)" : "rgba(255,255,255,0.5)",
                    fontSize: "1.04rem",
                    fontFamily: "inherit",
                    letterSpacing: "0.01em",
                    lineHeight: 1.2,
                    whiteSpace: "nowrap",
                    wordBreak: "keep-all",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    cursor: "pointer",
                    boxSizing: "border-box",
                    marginBottom: "16px",
                    transition: "background 0.15s ease, color 0.15s ease, border-color 0.15s ease",
                    flexShrink: 0,
                }}
            >
                <span style={{ display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, width: 20, height: 20 }}>
                    <IcPencil />
                </span>
                {showExpanded && (
                    <span style={{ whiteSpace: "nowrap", wordBreak: "keep-all", overflow: "hidden", textOverflow: "ellipsis", display: "block", minWidth: 0, flex: 1 }}>
                        새 대화
                    </span>
                )}
            </button>

            {/* 상단 내비 */}
            <nav className="side-nav">
                <SideItem icon={<IcHome />} label="홈으로" href="/" expanded={showExpanded} />
                <SideItem icon={<IcUpload />} label="파일 업로드" href="/upload/commentary" expanded={showExpanded} />
                <SideItem icon={<IcExam />} label="가상 모의고사" href="/test_exam" expanded={showExpanded} />
                <SideItem icon={<IcPlan />} label="학습 분석 & AI 플랜" href="/study-plan" expanded={showExpanded} />
                <SideItem icon={<IcUser />} label="사용자 정보" href="/user" expanded={showExpanded} />
            </nav>

            {/* 하단 액션 */}
            <div className="side-bottom">
                <div className="side-divider" />
                <SideItem icon={<IcSettings />} label="설정" onClick={() => { setIsSettingsOpen(true); if (isMobile) setMobileOpen(false); }} expanded={showExpanded} />
                <SideItem icon={<IcInfo />} label="정보" onClick={() => { setIsInfoOpen(true); if (isMobile) setMobileOpen(false); }} expanded={showExpanded} />
                <SideItem icon={<IcLogout />} label="로그아웃" onClick={handleLogout} expanded={showExpanded} danger />
            </div>
        </aside>
    );

    return (
        <div className="layout">
            {/* 모바일 백드롭 */}
            {isMobile && mobileOpen && (
                <div className="mobile-backdrop" onClick={() => setMobileOpen(false)} />
            )}

            {/* 사이드바 */}
            {(sidebarVisible || isMobile) && sidebar}

            {/* 메인 영역 */}
            <div className={`main ${!isMobile && !sideExpanded ? "main-collapsed" : ""} ${!isMobile && sideExpanded ? "main-expanded" : ""}`}>

                {/* 모바일 전용 헤더 */}
                {isMobile && (
                    <header className="mobile-header">
                        <button className="icon-btn" onClick={() => setMobileOpen(true)} aria-label="메뉴">
                            <IcMenu />
                        </button>
                        <a href="/" className="mobile-logo">공잘알</a>
                        <div style={{ width: 36 }} />
                    </header>
                )}

                {/* 메시지 영역 */}
                <main className="chat-messages">
                    {messages.map((m, i) => (
                        <div key={i} className={`message ${m.role === "user" ? "message-user" : "message-bot"}`}>
                            {m.role === "bot" && <span className="bot-avatar">공</span>}
                            <div className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-bot"}`}>
                                {m.role === "bot" && m.mode && m.mode !== "chat" && (
                                    <div className="badge-row">
                                        <span className={`mode-badge mode-${m.mode}`}>
                                            {m.mode === "mentoring" ? "🎓 멘토링" :
                                                m.mode === "exam" ? "📝 시험" :
                                                    m.mode === "study_plan" ? "📅 학습계획" :
                                                        m.mode === "block" ? "🚫 차단" : m.mode}
                                        </span>
                                        {m.koelectra?.gateway && (
                                            <span className={`koelectra-badge koelectra-${m.koelectra.gateway?.toLowerCase()}`}>
                                                {m.koelectra.method === "keyword_fallback" ? "🔤" : "🤖"}{" "}
                                                {m.koelectra.gateway}
                                                {m.koelectra.confidence != null && (
                                                    <span className="koelectra-conf">
                                                        {(m.koelectra.confidence * 100).toFixed(0)}%
                                                    </span>
                                                )}
                                            </span>
                                        )}
                                    </div>
                                )}
                                <div className="message-text">
                                    {m.text.split("\n").map((line, j) => (
                                        <span key={j}>
                                            {line.startsWith("📋") || line.startsWith("💡") || line.startsWith("📌")
                                                ? <strong>{line}</strong>
                                                : line.startsWith("---")
                                                    ? <hr className="message-divider" />
                                                    : line}
                                            {j < m.text.split("\n").length - 1 && <br />}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="message message-bot">
                            <span className="bot-avatar">공</span>
                            <div className="bubble bubble-bot">
                                <span className="typing-dots">
                                    <span className="dot dot-1" /><span className="dot dot-2" /><span className="dot dot-3" />
                                </span>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </main>

                {/* 입력 영역 */}
                <footer className="chat-input-area">
                    <div className="input-wrapper">
                        <input
                            className="chat-input"
                            type="text"
                            placeholder="메시지를 입력하세요..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                        />
                        <button
                            className={`send-btn ${input.trim() ? "active" : ""}`}
                            onClick={sendMessage}
                            disabled={!input.trim() || isLoading}
                            aria-label="전송"
                        >
                            <IcSend />
                        </button>
                    </div>
                </footer>
            </div>

            {/* ── 설정 다이얼로그 ── */}
            <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
                <DialogContent className="!bg-[#0a0a0a] !border-[rgba(255,255,255,0.08)]">
                    <DialogHeader>
                        <DialogTitle className="!text-white">설정</DialogTitle>
                        <DialogDescription className="!text-[rgba(255,255,255,0.4)]">채팅봇 설정을 변경할 수 있습니다.</DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                        <p className="text-sm" style={{ color: "rgba(255,255,255,0.3)" }}>설정 옵션이 여기에 표시됩니다.</p>
                    </div>
                </DialogContent>
            </Dialog>

            {/* ── 정보 다이얼로그 ── */}
            <Dialog open={isInfoOpen} onOpenChange={setIsInfoOpen}>
                <DialogContent className="!bg-[#0a0a0a] !border-[rgba(255,255,255,0.08)]">
                    <DialogHeader>
                        <DialogTitle className="!text-white">정보</DialogTitle>
                        <DialogDescription className="!text-[rgba(255,255,255,0.4)]">공잘알에 대한 정보입니다.</DialogDescription>
                    </DialogHeader>
                    <div className="py-4 space-y-3">
                        <p className="text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>
                            <span style={{ color: "rgba(255,255,255,0.7)" }}>버전</span>&nbsp;1.0.0
                        </p>
                        <p className="text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>
                            <span style={{ color: "rgba(255,255,255,0.7)" }}>설명</span>&nbsp;공무원 시험, 잘 알려주는 AI
                        </p>
                    </div>
                </DialogContent>
            </Dialog>

            <style jsx>{`
                /* ── 전체 레이아웃 ── */
                .layout {
                    display: flex;
                    flex-direction: row;
                    height: 100vh;
                    width: 100vw;
                    background: #000;
                    font-family: "Gothic A1","Noto Sans KR","Malgun Gothic",sans-serif;
                    overflow: hidden;
                    position: relative;
                }

                /* ── 사이드바 ── */
                .sidebar {
                    width: 356px;
                    min-width: 356px;
                    max-width: 356px;
                    height: 100vh;
                    background: #0d0d0d;
                    border-right: 1px solid rgba(255,255,255,0.06);
                    display: flex;
                    flex-direction: column;
                    padding: 12px 12px 18px;
                    overflow: hidden;
                    transition: width 0.22s ease, min-width 0.22s ease, max-width 0.22s ease;
                    flex-shrink: 0;
                    box-sizing: border-box;
                }
                .sidebar-collapsed {
                    width: 72px;
                    min-width: 72px;
                    max-width: 72px;
                    padding: 12px 8px 18px;
                }
                .sidebar-mobile {
                    position: fixed;
                    left: 0; top: 0; bottom: 0;
                    z-index: 200;
                    width: min(90vw, 356px);
                    min-width: 0;
                    max-width: 356px;
                    box-shadow: 8px 0 32px rgba(0,0,0,0.7);
                }

                /* 상단 영역 */
                .side-top {
                    display: flex;
                    flex-direction: row;
                    flex-wrap: nowrap;
                    align-items: center;
                    gap: 14px;
                    padding: 8px 6px 16px;
                    margin-bottom: 4px;
                    flex-shrink: 0;
                }
                .side-toggle {
                    flex-shrink: 0;
                    width: 56px; height: 56px;
                    display: flex; align-items: center; justify-content: center;
                    border: none; border-radius: 12px;
                    background: transparent;
                    color: rgba(255,255,255,0.3);
                    cursor: pointer;
                    transition: color 0.18s, background 0.18s;
                }
                .side-toggle:hover {
                    color: rgba(255,255,255,0.75);
                    background: rgba(255,255,255,0.06);
                }
                .side-logo {
                    font-size: 2.35rem; font-weight: 900;
                    color: rgba(255,255,255,0.98);
                    text-decoration: none;
                    letter-spacing: 0.01em;
                    line-height: 1;
                    text-shadow: 0 0 24px rgba(255,255,255,0.14);
                    white-space: nowrap;
                    overflow: hidden;
                    flex-shrink: 1;
                    min-width: 0;
                }

                /* 새 대화 버튼 */
                .side-new-chat {
                    display: flex;
                    flex-direction: row;
                    flex-wrap: nowrap;
                    align-items: center;
                    gap: 12px;
                    width: 100%;
                    padding: 11px 14px;
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 9px;
                    background: transparent;
                    color: rgba(255,255,255,0.5);
                    font-size: 0.92rem; font-family: inherit;
                    letter-spacing: 0.015em;
                    cursor: pointer;
                    transition: background 0.18s ease, color 0.18s ease, border-color 0.18s ease;
                    margin-bottom: 18px;
                    white-space: nowrap;
                    overflow: hidden;
                    box-sizing: border-box;
                    flex-shrink: 0;
                }
                .side-new-chat:hover {
                    background: rgba(255,255,255,0.05);
                    color: rgba(255,255,255,0.88);
                    border-color: rgba(255,255,255,0.13);
                }
                .side-new-chat-icon {
                    justify-content: center;
                    padding: 10px;
                    gap: 0;
                }

                /* 내비 */
                .side-nav {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                    overflow-y: auto;
                    overflow-x: hidden;
                }
                .side-nav::-webkit-scrollbar { width: 2px; }
                .side-nav::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.05); }

                /* 사이드바 하단 */
                .side-bottom {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                    flex-shrink: 0;
                }
                .side-divider {
                    height: 1px;
                    background: rgba(255,255,255,0.06);
                    margin: 8px 4px 10px;
                }

                /* ── 메인 영역 ── */
                .main {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                    overflow: hidden;
                    min-width: 0;
                    transition: margin-left 0.25s ease;
                }

                /* ── 모바일 헤더 ── */
                .mobile-header {
                    display: flex; align-items: center; justify-content: space-between;
                    padding: 14px 16px;
                    border-bottom: 1px solid rgba(255,255,255,0.04);
                    background: rgba(0,0,0,0.7);
                    backdrop-filter: blur(12px);
                    flex-shrink: 0;
                }
                .mobile-logo {
                    font-size: 1.9rem; font-weight: 900; color: #fff;
                    text-decoration: none; letter-spacing: 0.01em;
                    line-height: 1;
                    text-shadow: 0 0 18px rgba(255,255,255,0.12);
                }
                .icon-btn {
                    width: 52px; height: 52px;
                    display: flex; align-items: center; justify-content: center;
                    border: none; border-radius: 12px;
                    background: transparent; color: rgba(255,255,255,0.35);
                    cursor: pointer; transition: all 0.2s ease;
                }
                .icon-btn:hover { color: rgba(255,255,255,0.8); background: rgba(255,255,255,0.05); }

                /* ── 모바일 백드롭 ── */
                .mobile-backdrop {
                    position: fixed; inset: 0; z-index: 199;
                    background: rgba(0,0,0,0.55);
                    backdrop-filter: blur(2px);
                }

                /* ── 채팅 메시지 ── */
                .chat-messages {
                    flex: 1; overflow-y: auto;
                    padding: 24px 20px;
                    display: flex; flex-direction: column; gap: 20px;
                }
                .chat-messages::-webkit-scrollbar { width: 4px; }
                .chat-messages::-webkit-scrollbar-track { background: transparent; }
                .chat-messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.07); border-radius: 4px; }

                .message {
                    display: flex; gap: 12px;
                    max-width: 720px; width: 100%; margin: 0 auto;
                    animation: msgIn 0.3s ease-out;
                }
                @keyframes msgIn {
                    from { opacity:0; transform:translateY(8px); }
                    to   { opacity:1; transform:translateY(0); }
                }
                .message-user { flex-direction: row-reverse; }

                .bot-avatar {
                    flex-shrink: 0; width: 32px; height: 32px;
                    border-radius: 10px;
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.08);
                    display: flex; align-items: center; justify-content: center;
                    font-size: 0.75rem; font-weight: 700;
                    color: rgba(255,255,255,0.5); margin-top: 2px;
                }

                .bubble {
                    max-width: 75%; padding: 12px 16px;
                    border-radius: 16px; font-size: 0.9rem;
                    line-height: 1.6; letter-spacing: 0.01em;
                }
                .bubble-bot {
                    background: rgba(255,255,255,0.04);
                    border: 1px solid rgba(255,255,255,0.06);
                    color: rgba(255,255,255,0.8);
                    border-top-left-radius: 4px;
                }
                .bubble-user {
                    background: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.9);
                    border-top-right-radius: 4px;
                }

                .badge-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
                .mode-badge { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.03em; }
                .mode-mentoring { background: rgba(99,102,241,0.15); color: rgba(165,168,255,0.9); border: 1px solid rgba(99,102,241,0.2); }
                .mode-exam      { background: rgba(52,211,153,0.15); color: rgba(110,231,183,0.9); border: 1px solid rgba(52,211,153,0.2); }
                .mode-study_plan{ background: rgba(251,191,36,0.15); color: rgba(253,224,71,0.9);  border: 1px solid rgba(251,191,36,0.2); }
                .mode-block     { background: rgba(239,68,68,0.15);  color: rgba(252,165,165,0.9); border: 1px solid rgba(239,68,68,0.2); }

                .koelectra-badge { display: inline-flex; align-items: center; gap: 3px; padding: 2px 7px; border-radius: 6px; font-size: 0.62rem; font-weight: 600; letter-spacing: 0.03em; opacity: 0.7; }
                .koelectra-conf  { font-size: 0.58rem; opacity: 0.7; margin-left: 2px; }
                .koelectra-policy_based { background: rgba(139,92,246,0.12); color: rgba(196,181,253,0.9); border: 1px solid rgba(139,92,246,0.15); }
                .koelectra-rule_based   { background: rgba(34,197,94,0.12);  color: rgba(134,239,172,0.9); border: 1px solid rgba(34,197,94,0.15); }
                .koelectra-block        { background: rgba(239,68,68,0.12);  color: rgba(252,165,165,0.9); border: 1px solid rgba(239,68,68,0.15); }

                .message-text { white-space: pre-wrap; word-break: break-word; }
                .message-divider { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 8px 0; }

                /* 타이핑 */
                .typing-dots { display: flex; gap: 4px; padding: 4px 0; }
                .dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.3); animation: dotB 1.4s ease-in-out infinite; }
                .dot-1 { animation-delay: 0s; } .dot-2 { animation-delay: 0.2s; } .dot-3 { animation-delay: 0.4s; }
                @keyframes dotB {
                    0%,80%,100% { transform:scale(0.6); opacity:0.3; }
                    40%         { transform:scale(1);   opacity:1; }
                }

                /* ── 입력 영역 ── */
                .chat-input-area {
                    padding: 14px 20px 22px;
                    border-top: 1px solid rgba(255,255,255,0.04);
                    background: rgba(0,0,0,0.5);
                    backdrop-filter: blur(12px);
                    flex-shrink: 0;
                }
                .input-wrapper {
                    max-width: 720px; margin: 0 auto;
                    display: flex; align-items: center; gap: 8px;
                    padding: 6px 6px 6px 18px;
                    background: rgba(255,255,255,0.04);
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 24px;
                    transition: border-color 0.3s ease;
                }
                .input-wrapper:focus-within { border-color: rgba(255,255,255,0.14); }
                .chat-input {
                    flex: 1; background: transparent; border: none; outline: none;
                    color: #fff; font-size: 0.9rem; font-family: inherit; letter-spacing: 0.01em;
                }
                .chat-input::placeholder { color: rgba(255,255,255,0.2); }
                .send-btn {
                    width: 34px; height: 34px; flex-shrink: 0;
                    display: flex; align-items: center; justify-content: center;
                    border: none; border-radius: 50%;
                    background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.2);
                    cursor: pointer; transition: all 0.3s ease;
                }
                .send-btn.active { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.8); }
                .send-btn.active:hover { background: rgba(255,255,255,0.2); color: #fff; }
                .send-btn:disabled { cursor: not-allowed; }

                /* ── 반응형 ── */
                @media (max-width: 767px) {
                    .sidebar { display: none; }
                    .sidebar-mobile { display: flex; }
                    .chat-messages { padding: 16px 12px; gap: 14px; }
                    .bubble { max-width: 85%; padding: 10px 13px; font-size: 0.82rem; }
                    .chat-input-area { padding: 10px 12px 16px; }
                    .input-wrapper { padding: 4px 4px 4px 14px; border-radius: 20px; }
                    .chat-input { font-size: 0.82rem; }
                    .send-btn { width: 30px; height: 30px; }
                }
            `}</style>
        </div>
    );
}
