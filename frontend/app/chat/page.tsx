"use client";

import { useState, useRef, useEffect } from "react";
import { logout } from "@/lib/auth-api";
import { useUser } from "@/lib/hooks/useUser";
import { isGuestEntryActive } from "@/lib/guest-session";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";

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

// 세션 ID 생성 유틸
function generateSessionId() {
    return "sess_" + crypto.randomUUID().replace(/-/g, "").slice(0, 16);
}

// sessionStorage 키
const STORAGE_KEY_MESSAGES = "chat_messages";
const STORAGE_KEY_THREAD_ID = "chat_thread_id";

// 초기 환영 메시지
const WELCOME_MESSAGE: ChatMessage = {
    role: "bot",
    text: "안녕하세요! 공잘알 AI 멘토입니다.\n\n공무원 시험 준비에 대해 무엇이든 물어보세요.\n합격 수기 4,910건의 데이터를 기반으로 맞춤 조언을 드립니다.\n\n💡 예시 질문:\n• 노베이스 1년 일행직 어떻게 준비해?\n• 행정법 교재 추천해줘\n• 단기 합격 학습 계획 짜줘\n• 독학 vs 학원 어떤게 나을까?",
};

/** sessionStorage에서 대화 이력 복원 */
function loadMessagesFromStorage(): ChatMessage[] {
    if (typeof window === "undefined") return [WELCOME_MESSAGE];
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY_MESSAGES);
        if (raw) {
            const parsed = JSON.parse(raw) as ChatMessage[];
            if (Array.isArray(parsed) && parsed.length > 0) return parsed;
        }
    } catch { /* 파싱 실패 시 기본값 */ }
    return [WELCOME_MESSAGE];
}

/** sessionStorage에서 세션 ID 복원 */
function loadThreadIdFromStorage(): string {
    if (typeof window === "undefined") return generateSessionId();
    try {
        const saved = sessionStorage.getItem(STORAGE_KEY_THREAD_ID);
        if (saved) return saved;
    } catch { /* 실패 시 새로 생성 */ }
    const newId = generateSessionId();
    sessionStorage.setItem(STORAGE_KEY_THREAD_ID, newId);
    return newId;
}

export default function ChatbotUI() {
    const { user, loading: userLoading } = useUser();
    const [guestBanner, setGuestBanner] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isInfoOpen, setIsInfoOpen] = useState(false);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    // 멀티턴 대화 세션 ID (sessionStorage에서 복원)
    const threadIdRef = useRef<string>("");
    const authReadyRef = useRef(false);

    // 비로그인: 대화 이력 저장 안 함 / 로그인: sessionStorage 복원·저장
    useEffect(() => {
        if (userLoading) return;
        if (authReadyRef.current) return;
        authReadyRef.current = true;
        setGuestBanner(isGuestEntryActive());
        if (user) {
            const restored = loadMessagesFromStorage();
            setMessages(restored);
            threadIdRef.current = loadThreadIdFromStorage();
        } else {
            setMessages([WELCOME_MESSAGE]);
            threadIdRef.current = generateSessionId();
        }
    }, [userLoading, user]);

    // ── messages 변경 시 sessionStorage에 저장 (로그인 사용자만) ──
    useEffect(() => {
        if (userLoading || !user) return;
        if (messages.length <= 1 && messages[0]?.text === WELCOME_MESSAGE.text) {
            return;
        }
        try {
            sessionStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(messages));
        } catch { /* 용량 초과 등 무시 */ }
    }, [messages, userLoading, user]);

    const handleLogout = () => {
        setIsMenuOpen(false);
        logout(); // 백엔드 리다이렉트로 쿠키 삭제 + /login 이동
    };

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

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
                    text:
                        typeof data?.answer === "string"
                            ? data.answer
                            : data?.error || "응답을 생성하지 못했습니다.",
                    mode: data?.mode,
                    retrieved_docs: data?.retrieved_docs,
                    koelectra: data?.koelectra ?? null,
                },
            ]);
        } catch {
            setMessages((prev) => [
                ...prev,
                { role: "bot", text: "오류가 발생했습니다. 잠시 후 다시 시도해 주세요." },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-container">
            {/* ── 헤더 ── */}
            <header className="chat-header">
                <a href="/" className="header-logo">
                    <span>공</span><span>잘</span><span>알</span>
                </a>

                <div className="header-actions">
                    <button
                        className="icon-btn"
                        onClick={() => setIsInfoOpen(true)}
                        aria-label="정보"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10" />
                            <path d="M12 16v-4" />
                            <path d="M12 8h.01" />
                        </svg>
                    </button>
                    <button
                        className="icon-btn"
                        onClick={() => setIsSettingsOpen(true)}
                        aria-label="설정"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                            <circle cx="12" cy="12" r="3" />
                        </svg>
                    </button>
                    <button
                        className="icon-btn"
                        onClick={() => setIsMenuOpen(true)}
                        aria-label="메뉴"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="4" x2="20" y1="12" y2="12" />
                            <line x1="4" x2="20" y1="6" y2="6" />
                            <line x1="4" x2="20" y1="18" y2="18" />
                        </svg>
                    </button>
                </div>
            </header>

            {!userLoading && !user && guestBanner && (
                <div className="guest-chat-banner">
                    <span>👤</span>
                    <span>게스트(임시) — 대화·풀이 기록은 브라우저를 닫으면 사라집니다. DB에 저장되지 않습니다.</span>
                    <a href="/login">로그인</a>
                </div>
            )}

            {/* ── 메시지 영역 ── */}
            <main className="chat-messages">
                {messages.map((m, i) => (
                    <div
                        key={i}
                        className={`message ${m.role === "user" ? "message-user" : "message-bot"}`}
                    >
                        {m.role === "bot" && (
                            <span className="bot-avatar">공</span>
                        )}
                        <div className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-bot"}`}>
                            {m.role === "bot" && m.mode && m.mode !== "chat" && (
                                <div className="badge-row">
                                    <span className={`mode-badge mode-${m.mode}`}>
                                        {m.mode === "mentoring" ? "🎓 멘토링" :
                                            m.mode === "exam" ? "📝 시험" :
                                                m.mode === "study_plan" ? "📅 학습계획" :
                                                    m.mode === "block" ? "🚫 차단" :
                                                        m.mode}
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
                                        {line.startsWith("📋") || line.startsWith("💡") || line.startsWith("📌") ? (
                                            <strong>{line}</strong>
                                        ) : line.startsWith("---") ? (
                                            <hr className="message-divider" />
                                        ) : (
                                            line
                                        )}
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
                                <span className="dot dot-1" />
                                <span className="dot dot-2" />
                                <span className="dot dot-3" />
                            </span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </main>

            {/* ── 입력 영역 ── */}
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
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="m22 2-7 20-4-9-9-4Z" />
                            <path d="M22 2 11 13" />
                        </svg>
                    </button>
                </div>
            </footer>

            {/* ── 사이드 메뉴 (Sheet) ── */}
            <Sheet open={isMenuOpen} onOpenChange={setIsMenuOpen}>
                <SheetContent side="right" className="!bg-[#0a0a0a] !border-l-[rgba(255,255,255,0.06)]">
                    <SheetHeader>
                        <SheetTitle className="!text-white">메뉴</SheetTitle>
                        <SheetDescription className="sr-only">메뉴</SheetDescription>
                    </SheetHeader>
                    <nav className="flex flex-col gap-1 mt-6">
                        <a href="/" className="menu-item">홈으로</a>
                        <button className="menu-item" onClick={() => {
                            // 새 세션 생성
                            const newId = generateSessionId();
                            threadIdRef.current = newId;
                            sessionStorage.setItem(STORAGE_KEY_THREAD_ID, newId);
                            // 대화 이력 초기화
                            const freshMessages: ChatMessage[] = [WELCOME_MESSAGE];
                            setMessages(freshMessages);
                            sessionStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(freshMessages));
                            setIsMenuOpen(false);
                        }}>새 대화</button>
                        <a href="/upload/commentary" className="menu-item">파일 업로드</a>
                        <a href="/test_exam" className="menu-item">가상 모의고사</a>
                        <a href="/study-plan" className="menu-item">학습 분석 & AI 플랜</a>
                        <div className="menu-divider" />
                        <a href="/user" className="menu-item">사용자 정보</a>
                        <button className="menu-item" onClick={() => { setIsMenuOpen(false); setIsSettingsOpen(true); }}>설정</button>
                        <button className="menu-item" onClick={() => { setIsMenuOpen(false); setIsInfoOpen(true); }}>정보</button>
                        <div className="menu-divider" />
                        <button className="menu-item menu-item-logout" onClick={handleLogout}>로그아웃</button>
                    </nav>
                </SheetContent>
            </Sheet>

            {/* ── 설정 다이얼로그 ── */}
            <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
                <DialogContent className="!bg-[#0a0a0a] !border-[rgba(255,255,255,0.08)]">
                    <DialogHeader>
                        <DialogTitle className="!text-white">설정</DialogTitle>
                        <DialogDescription className="!text-[rgba(255,255,255,0.4)]">
                            채팅봇 설정을 변경할 수 있습니다.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                        <p className="text-sm" style={{ color: "rgba(255,255,255,0.3)" }}>
                            설정 옵션이 여기에 표시됩니다.
                        </p>
                    </div>
                </DialogContent>
            </Dialog>

            {/* ── 정보 다이얼로그 ── */}
            <Dialog open={isInfoOpen} onOpenChange={setIsInfoOpen}>
                <DialogContent className="!bg-[#0a0a0a] !border-[rgba(255,255,255,0.08)]">
                    <DialogHeader>
                        <DialogTitle className="!text-white">정보</DialogTitle>
                        <DialogDescription className="!text-[rgba(255,255,255,0.4)]">
                            공잘알에 대한 정보입니다.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-4 space-y-3">
                        <p className="text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>
                            <span style={{ color: "rgba(255,255,255,0.7)" }}>버전</span> &nbsp;1.0.0
                        </p>
                        <p className="text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>
                            <span style={{ color: "rgba(255,255,255,0.7)" }}>설명</span> &nbsp;공무원 시험, 잘 알려주는 AI
                        </p>
                    </div>
                </DialogContent>
            </Dialog>

            <style jsx>{`
                /* ── 컨테이너 ── */
                .chat-container {
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                    width: 100vw;
                    background: #000;
                    font-family:
                        "Gothic A1",
                        "Noto Sans KR",
                        "Malgun Gothic",
                        "맑은 고딕",
                        sans-serif;
                }

                /* ── 헤더 ── */
                .chat-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 16px 20px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
                    background: rgba(0, 0, 0, 0.6);
                    backdrop-filter: blur(12px);
                    position: sticky;
                    top: 0;
                    z-index: 10;
                }

                .guest-chat-banner {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    flex-wrap: wrap;
                    padding: 8px 16px;
                    font-size: 0.72rem;
                    color: rgba(251, 191, 36, 0.75);
                    background: rgba(251, 191, 36, 0.06);
                    border-bottom: 1px solid rgba(251, 191, 36, 0.1);
                }
                .guest-chat-banner a {
                    color: rgba(251, 191, 36, 0.95);
                    font-weight: 600;
                    margin-left: auto;
                }

                .header-logo {
                    display: flex;
                    gap: 2px;
                    text-decoration: none;
                    font-size: 1.2rem;
                    font-weight: 900;
                    color: #fff;
                    letter-spacing: 0.05em;
                }

                .header-actions {
                    display: flex;
                    gap: 4px;
                }

                .icon-btn {
                    width: 36px;
                    height: 36px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border: none;
                    border-radius: 8px;
                    background: transparent;
                    color: rgba(255, 255, 255, 0.3);
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .icon-btn:hover {
                    color: rgba(255, 255, 255, 0.8);
                    background: rgba(255, 255, 255, 0.05);
                }

                /* ── 메시지 영역 ── */
                .chat-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 24px 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }

                .chat-messages::-webkit-scrollbar {
                    width: 4px;
                }

                .chat-messages::-webkit-scrollbar-track {
                    background: transparent;
                }

                .chat-messages::-webkit-scrollbar-thumb {
                    background: rgba(255, 255, 255, 0.08);
                    border-radius: 4px;
                }

                .message {
                    display: flex;
                    gap: 12px;
                    max-width: 720px;
                    width: 100%;
                    margin: 0 auto;
                    animation: msgFadeIn 0.3s ease-out;
                }

                @keyframes msgFadeIn {
                    from {
                        opacity: 0;
                        transform: translateY(8px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                .message-user {
                    flex-direction: row-reverse;
                }

                .bot-avatar {
                    flex-shrink: 0;
                    width: 32px;
                    height: 32px;
                    border-radius: 10px;
                    background: rgba(255, 255, 255, 0.06);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.75rem;
                    font-weight: 700;
                    color: rgba(255, 255, 255, 0.5);
                    margin-top: 2px;
                }

                .bubble {
                    max-width: 75%;
                    padding: 12px 16px;
                    border-radius: 16px;
                    font-size: 0.9rem;
                    line-height: 1.6;
                    letter-spacing: 0.01em;
                }

                .bubble-bot {
                    background: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    color: rgba(255, 255, 255, 0.8);
                    border-top-left-radius: 4px;
                }

                .bubble-user {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    color: rgba(255, 255, 255, 0.9);
                    border-top-right-radius: 4px;
                }

                .mode-badge {
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 6px;
                    font-size: 0.7rem;
                    font-weight: 600;
                    letter-spacing: 0.03em;
                    margin-bottom: 8px;
                }

                .mode-mentoring {
                    background: rgba(99, 102, 241, 0.15);
                    color: rgba(165, 168, 255, 0.9);
                    border: 1px solid rgba(99, 102, 241, 0.2);
                }

                .mode-exam {
                    background: rgba(52, 211, 153, 0.15);
                    color: rgba(110, 231, 183, 0.9);
                    border: 1px solid rgba(52, 211, 153, 0.2);
                }

                .mode-study_plan {
                    background: rgba(251, 191, 36, 0.15);
                    color: rgba(253, 224, 71, 0.9);
                    border: 1px solid rgba(251, 191, 36, 0.2);
                }

                .mode-block {
                    background: rgba(239, 68, 68, 0.15);
                    color: rgba(252, 165, 165, 0.9);
                    border: 1px solid rgba(239, 68, 68, 0.2);
                }

                .badge-row {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    flex-wrap: wrap;
                    margin-bottom: 8px;
                }

                .koelectra-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 3px;
                    padding: 2px 7px;
                    border-radius: 6px;
                    font-size: 0.62rem;
                    font-weight: 600;
                    letter-spacing: 0.03em;
                    opacity: 0.7;
                }

                .koelectra-conf {
                    font-size: 0.58rem;
                    opacity: 0.7;
                    margin-left: 2px;
                }

                .koelectra-policy_based {
                    background: rgba(139, 92, 246, 0.12);
                    color: rgba(196, 181, 253, 0.9);
                    border: 1px solid rgba(139, 92, 246, 0.15);
                }

                .koelectra-rule_based {
                    background: rgba(34, 197, 94, 0.12);
                    color: rgba(134, 239, 172, 0.9);
                    border: 1px solid rgba(34, 197, 94, 0.15);
                }

                .koelectra-block {
                    background: rgba(239, 68, 68, 0.12);
                    color: rgba(252, 165, 165, 0.9);
                    border: 1px solid rgba(239, 68, 68, 0.15);
                }

                .message-text {
                    white-space: pre-wrap;
                    word-break: break-word;
                }

                .message-divider {
                    border: none;
                    border-top: 1px solid rgba(255, 255, 255, 0.08);
                    margin: 8px 0;
                }

                /* ── 타이핑 인디케이터 ── */
                .typing-dots {
                    display: flex;
                    gap: 4px;
                    padding: 4px 0;
                }

                .dot {
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.3);
                    animation: dotBounce 1.4s ease-in-out infinite;
                }

                .dot-1 { animation-delay: 0s; }
                .dot-2 { animation-delay: 0.2s; }
                .dot-3 { animation-delay: 0.4s; }

                @keyframes dotBounce {
                    0%, 80%, 100% {
                        transform: scale(0.6);
                        opacity: 0.3;
                    }
                    40% {
                        transform: scale(1);
                        opacity: 1;
                    }
                }

                /* ── 입력 영역 ── */
                .chat-input-area {
                    padding: 16px 20px 24px;
                    border-top: 1px solid rgba(255, 255, 255, 0.04);
                    background: rgba(0, 0, 0, 0.6);
                    backdrop-filter: blur(12px);
                }

                .input-wrapper {
                    max-width: 720px;
                    margin: 0 auto;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 6px 6px 6px 20px;
                    background: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 24px;
                    transition: border-color 0.3s ease;
                }

                .input-wrapper:focus-within {
                    border-color: rgba(255, 255, 255, 0.15);
                }

                .chat-input {
                    flex: 1;
                    background: transparent;
                    border: none;
                    outline: none;
                    color: #fff;
                    font-size: 0.9rem;
                    font-family: inherit;
                    letter-spacing: 0.01em;
                }

                .chat-input::placeholder {
                    color: rgba(255, 255, 255, 0.2);
                }

                .send-btn {
                    width: 36px;
                    height: 36px;
                    flex-shrink: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border: none;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.06);
                    color: rgba(255, 255, 255, 0.2);
                    cursor: pointer;
                    transition: all 0.3s ease;
                }

                .send-btn.active {
                    background: rgba(255, 255, 255, 0.12);
                    color: rgba(255, 255, 255, 0.8);
                }

                .send-btn.active:hover {
                    background: rgba(255, 255, 255, 0.2);
                    color: #fff;
                }

                .send-btn:disabled {
                    cursor: not-allowed;
                }

                /* ── 사이드 메뉴 아이템 ── */
                :global(.menu-item) {
                    display: block;
                    width: 100%;
                    padding: 10px 16px;
                    border: none;
                    border-radius: 8px;
                    background: transparent;
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 0.85rem;
                    font-family: inherit;
                    letter-spacing: 0.05em;
                    text-align: left;
                    text-decoration: none;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                :global(.menu-item:hover) {
                    color: rgba(255, 255, 255, 0.9);
                    background: rgba(255, 255, 255, 0.05);
                }

                :global(.menu-divider) {
                    height: 1px;
                    background: rgba(255, 255, 255, 0.06);
                    margin: 8px 0;
                }

                :global(.menu-item-logout) {
                    color: rgba(255, 100, 100, 0.6);
                }

                :global(.menu-item-logout:hover) {
                    color: rgba(255, 100, 100, 1);
                    background: rgba(255, 100, 100, 0.08);
                }

                /* ── 모바일 반응형 ── */
                @media (max-width: 640px) {
                    .chat-header {
                        padding: 12px 14px;
                    }
                    .header-logo {
                        font-size: 1rem;
                    }
                    .icon-btn {
                        width: 32px;
                        height: 32px;
                    }
                    .icon-btn svg {
                        width: 16px;
                        height: 16px;
                    }
                    .chat-messages {
                        padding: 16px 12px;
                        gap: 14px;
                    }
                    .message {
                        gap: 8px;
                    }
                    .bot-avatar {
                        width: 28px;
                        height: 28px;
                        font-size: 0.65rem;
                        border-radius: 8px;
                    }
                    .bubble {
                        max-width: 85%;
                        padding: 10px 13px;
                        font-size: 0.82rem;
                        border-radius: 14px;
                    }
                    .bubble-bot {
                        border-top-left-radius: 4px;
                    }
                    .bubble-user {
                        border-top-right-radius: 4px;
                    }
                    .mode-badge {
                        font-size: 0.62rem;
                        padding: 2px 6px;
                    }
                    .koelectra-badge {
                        font-size: 0.55rem;
                        padding: 2px 5px;
                    }
                    .koelectra-conf {
                        font-size: 0.5rem;
                    }
                    .chat-input-area {
                        padding: 10px 12px 16px;
                    }
                    .input-wrapper {
                        padding: 4px 4px 4px 14px;
                        gap: 6px;
                        border-radius: 20px;
                    }
                    .chat-input {
                        font-size: 0.82rem;
                    }
                    .send-btn {
                        width: 32px;
                        height: 32px;
                    }
                    .send-btn svg {
                        width: 15px;
                        height: 15px;
                    }
                }

                @media (max-width: 360px) {
                    .bubble {
                        max-width: 90%;
                        font-size: 0.78rem;
                    }
                    .chat-messages {
                        padding: 12px 8px;
                    }
                    .chat-input-area {
                        padding: 8px 8px 12px;
                    }
                }
            `}</style>
        </div>
    );
}
