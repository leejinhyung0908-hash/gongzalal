'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { API_BASE_URL } from '@/lib/auth-api';

export default function NaverCallbackPage() {
    const router = useRouter();

    useEffect(() => {
        console.log('[Auth] 네이버 로그인 성공, 리다이렉트 중...');

        // 로그인 성공 로그 기록 (백엔드로 직접 전송)
        fetch(`${API_BASE_URL}/api/log/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                action: '네이버 로그인 성공',
                url: window.location.href,
            }),
        }).catch(() => {});

        // 로그인 성공 후 채팅 페이지로 이동
        const timer = setTimeout(() => {
            router.replace('/chat');
        }, 1500);

        return () => clearTimeout(timer);
    }, [router]);

    return (
        <div style={{
            display: 'flex',
            minHeight: '100vh',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#000',
            color: '#fff',
            fontFamily: '"Gothic A1", "Noto Sans KR", sans-serif',
        }}>
            <div style={{ textAlign: 'center' }}>
                <div style={{
                    width: 48,
                    height: 48,
                    border: '3px solid rgba(255,255,255,0.1)',
                    borderTop: '3px solid #03C75A',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                    margin: '0 auto 20px',
                }} />
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.9rem' }}>
                    네이버 로그인 처리 중...
                </p>
                <style jsx>{`
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                `}</style>
            </div>
        </div>
    );
}

