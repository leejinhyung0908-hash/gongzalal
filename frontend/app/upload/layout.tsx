"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/auth-api";

const categories = [
    { id: "commentary", name: "해설", path: "/upload/commentary" },
    { id: "user", name: "사용자", path: "/upload/user" },
    { id: "exam", name: "시험", path: "/upload/exam" },
    { id: "question_image", name: "문제 이미지", path: "/upload/question_image" },
    { id: "mentoring", name: "멘토링 지식", path: "/upload/mentoring" },
];

export default function UploadLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    const handleLogout = async () => {
        const success = await logout();
        if (success) {
            window.location.href = "/login";
        } else {
            alert("로그아웃에 실패했습니다.");
        }
    };

    return (
        <div className="upload-layout">
            {/* 사이드바 */}
            <aside className="sidebar">
                <div className="sidebar-header">
                    <a href="/" className="sidebar-logo">
                        <span>공</span><span>잘</span><span>알</span>
                    </a>
                    <p className="sidebar-subtitle">파일 업로드</p>
                </div>

                <nav className="sidebar-nav">
                    {categories.map((cat) => (
                        <Link key={cat.id} href={cat.path as never} className="sidebar-nav-link">
                            <div className={`nav-item ${pathname === cat.path ? "active" : ""}`}>
                                <span className="nav-dot" />
                                <span className="nav-label">{cat.name}</span>
                            </div>
                        </Link>
                    ))}
                </nav>

                <div className="sidebar-footer">
                    <a href="/chat" className="footer-link">채팅으로</a>
                    <span className="footer-divider">·</span>
                    <a href="/" className="footer-link">메인으로</a>
                    <span className="footer-divider">·</span>
                    <button onClick={handleLogout} className="footer-link footer-logout">로그아웃</button>
                </div>
            </aside>

            {/* 콘텐츠 영역 */}
            <main className="upload-content">
                {children}
            </main>

            <style jsx>{`
                .upload-layout {
                    display: flex;
                    min-height: 100vh;
                    background: #000;
                    font-family:
                        "Gothic A1",
                        "Noto Sans KR",
                        "Malgun Gothic",
                        "맑은 고딕",
                        sans-serif;
                }

                /* ── 사이드바 ── */
                .sidebar {
                    width: 220px;
                    flex-shrink: 0;
                    display: flex;
                    flex-direction: column;
                    border-right: 1px solid rgba(255, 255, 255, 0.04);
                    background: rgba(255, 255, 255, 0.01);
                    backdrop-filter: blur(12px);
                }

                .sidebar-header {
                    padding: 28px 24px 24px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
                }

                .sidebar-logo {
                    display: flex;
                    gap: 2px;
                    text-decoration: none;
                    font-size: 1.3rem;
                    font-weight: 900;
                    color: #fff;
                    letter-spacing: 0.05em;
                    margin-bottom: 8px;
                }

                .sidebar-subtitle {
                    font-size: 0.7rem;
                    color: rgba(255, 255, 255, 0.25);
                    letter-spacing: 0.15em;
                    margin: 0;
                }

                /* ── 네비게이션 ── */
                .sidebar-nav {
                    flex: 1;
                    padding: 16px 12px;
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }

                :global(.sidebar-nav-link) {
                    text-decoration: none !important;
                }

                .nav-item {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 10px 14px;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .nav-item:hover {
                    background: rgba(255, 255, 255, 0.04);
                }

                .nav-item.active {
                    background: rgba(255, 255, 255, 0.06);
                }

                .nav-dot {
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.15);
                    transition: all 0.2s ease;
                }

                .nav-item.active .nav-dot {
                    background: rgba(255, 255, 255, 0.7);
                    box-shadow: 0 0 8px rgba(255, 255, 255, 0.3);
                }

                .nav-label {
                    font-size: 0.85rem;
                    color: rgba(255, 255, 255, 0.4);
                    letter-spacing: 0.05em;
                    transition: color 0.2s ease;
                }

                .nav-item:hover .nav-label {
                    color: rgba(255, 255, 255, 0.7);
                }

                .nav-item.active .nav-label {
                    color: rgba(255, 255, 255, 0.9);
                    font-weight: 500;
                }

                /* ── 하단 ── */
                .sidebar-footer {
                    padding: 16px 24px;
                    border-top: 1px solid rgba(255, 255, 255, 0.04);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                }

                .footer-link {
                    color: rgba(255, 255, 255, 0.2);
                    font-size: 0.7rem;
                    letter-spacing: 0.05em;
                    text-decoration: none;
                    transition: color 0.2s ease;
                }

                .footer-link:hover {
                    color: rgba(255, 255, 255, 0.6);
                }

                .footer-divider {
                    color: rgba(255, 255, 255, 0.1);
                    font-size: 0.7rem;
                }

                .footer-logout {
                    background: none;
                    border: none;
                    cursor: pointer;
                    font-family: inherit;
                    padding: 0;
                }

                .footer-logout:hover {
                    color: rgba(255, 100, 100, 0.7) !important;
                }

                /* ── 콘텐츠 ── */
                .upload-content {
                    flex: 1;
                    overflow-y: auto;
                }

                /* ── 모바일 대응 ── */
                @media (max-width: 768px) {
                    .upload-layout {
                        flex-direction: column;
                    }
                    .sidebar {
                        width: 100%;
                        border-right: none;
                        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
                    }
                    .sidebar-header {
                        padding: 16px 16px 12px;
                        display: flex;
                        align-items: center;
                        gap: 12px;
                        border-bottom: none;
                    }
                    .sidebar-logo {
                        font-size: 1rem;
                        margin-bottom: 0;
                    }
                    .sidebar-subtitle {
                        font-size: 0.65rem;
                    }
                    .sidebar-nav {
                        flex-direction: row;
                        padding: 4px 12px 10px;
                        gap: 4px;
                        overflow-x: auto;
                        -webkit-overflow-scrolling: touch;
                        scrollbar-width: none;
                    }
                    .sidebar-nav::-webkit-scrollbar {
                        display: none;
                    }
                    .nav-item {
                        padding: 6px 12px;
                        white-space: nowrap;
                        gap: 6px;
                    }
                    .nav-dot {
                        width: 5px;
                        height: 5px;
                    }
                    .nav-label {
                        font-size: 0.75rem;
                    }
                    .sidebar-footer {
                        display: none;
                    }
                }

                @media (max-width: 480px) {
                    .sidebar-header {
                        padding: 12px 12px 8px;
                    }
                    .nav-item {
                        padding: 5px 10px;
                    }
                    .nav-label {
                        font-size: 0.7rem;
                    }
                }
            `}</style>
        </div>
    );
}
