/**
 * 로그인된 사용자 정보를 관리하는 커스텀 훅.
 *
 * 사용법:
 *   const { user, loading } = useUser();
 *   // user?.id         → DB 정수 ID (solving_logs, study_plans 등 FK 참조용)
 *   // user?.social_id  → 소셜 로그인 원본 ID
 *   // user?.display_name → 닉네임
 *   // user?.provider   → 'kakao' | 'naver' | 'google'
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { getCurrentUser, storeLinkedProviders, clearForceReauth } from "@/lib/auth-api";
import { clearGuestSessionData } from "@/lib/guest-session";

export interface LinkedAccount {
    provider: string;
    social_id: string;
    email: string | null;
    linked_at: string | null;
}

export interface UserInfo {
    id: number | null;          // DB 정수 user_id (FK 참조용)
    social_id: string;          // 소셜 로그인 원본 ID
    display_name: string | null;
    provider: string | null;
    linked_accounts?: LinkedAccount[];
}

interface UseUserReturn {
    user: UserInfo | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

export function useUser(): UseUserReturn {
    const [user, setUser] = useState<UserInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchUser = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getCurrentUser();
            if (data && data.id !== undefined) {
                setUser(data as UserInfo);
                // 로그인 성공 → 게스트 임시 저장소 초기화 (일회성 세션 종료)
                clearGuestSessionData();

                // ── 연동 프로바이더 localStorage 동기화 ──
                // 로그인 상태가 확인될 때마다 최신 연동 정보를 localStorage에 저장.
                // 로그아웃 후에도 이 정보가 유지되어 미연동 프로바이더 로그인을 차단.
                const providers: string[] = [];
                if (data.linked_accounts) {
                    data.linked_accounts.forEach((acc) => {
                        if (acc.provider && !providers.includes(acc.provider)) {
                            providers.push(acc.provider);
                        }
                    });
                }
                if (data.provider && !providers.includes(data.provider)) {
                    providers.push(data.provider);
                }
                if (providers.length > 0) {
                    storeLinkedProviders(providers);
                }

                // ── 로그인 성공 → 재인증 플래그 제거 ──
                // 로그아웃 시 설정된 force_reauth 플래그는
                // 로그인이 완료된 후에야 삭제합니다.
                clearForceReauth();
            } else {
                setUser(null);
            }
        } catch (err) {
            console.warn("[useUser] 사용자 정보 가져오기 실패:", err);
            setError("사용자 정보를 가져올 수 없습니다.");
            setUser(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    return { user, loading, error, refetch: fetchUser };
}

