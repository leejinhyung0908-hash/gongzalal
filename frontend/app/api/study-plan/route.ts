/**
 * 학습 계획 관련 API 라우트
 * - POST: AI 학습 계획 생성 (분석 + RAG + EXAONE)
 */

// Next.js Route Segment Config — EXAONE 생성 시간 고려
export const maxDuration = 300; // 5분
export const dynamic = "force-dynamic";

type GenerateRequest = {
    user_id: number;
    question?: string;
};

type AnalyzeRequest = {
    user_id: number;
};

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const { action } = body;

        const backendUrl =
            process.env.NEXT_PUBLIC_API_URL ||
            process.env.NEXT_PUPLIC_API_URL ||
            "http://localhost:8000";

        if (action === "analyze") {
            // 풀이 로그 분석만
            const { user_id } = body as AnalyzeRequest;
            const response = await fetch(
                `${backendUrl}/api/v1/admin/study-plans/analyze/${user_id}`,
                { signal: AbortSignal.timeout(30000) }
            );

            if (!response.ok) {
                const errorText = await response.text();
                return Response.json(
                    { error: "분석 요청 실패", details: errorText },
                    { status: response.status }
                );
            }

            return Response.json(await response.json());
        }

        if (action === "read_latest") {
            // 최신 학습 계획 조회
            const { user_id } = body as AnalyzeRequest;
            const response = await fetch(
                `${backendUrl}/api/v1/admin/study-plans/user/${user_id}/latest`,
                { signal: AbortSignal.timeout(15000) }
            );

            if (!response.ok) {
                if (response.status === 404) {
                    return Response.json({ success: false, error: "생성된 학습 계획이 없습니다." });
                }
                const errorText = await response.text();
                return Response.json(
                    { error: "학습 계획 조회 실패", details: errorText },
                    { status: response.status }
                );
            }

            return Response.json(await response.json());
        }

        if (action === "generate") {
            // AI 학습 계획 생성
            const { user_id, question } = body as GenerateRequest & { action: string };
            const response = await fetch(
                `${backendUrl}/api/v1/admin/study-plans/generate`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        user_id,
                        question: question || "내 풀이 데이터를 분석해서 학습 계획을 세워줘",
                    }),
                    signal: AbortSignal.timeout(300000), // 5분 — EXAONE + RAG 프로필 매칭 시간 고려
                }
            );

            if (!response.ok) {
                const errorText = await response.text();
                return Response.json(
                    { error: "학습 계획 생성 실패", details: errorText },
                    { status: response.status }
                );
            }

            return Response.json(await response.json());
        }

        if (action === "generate_guest") {
            const { question, guest_profile, guest_logs } = body as {
                action: string;
                question?: string;
                guest_profile?: Record<string, unknown>;
                guest_logs?: unknown[];
            };
            const response = await fetch(`${backendUrl}/api/v1/admin/study-plans/generate-guest`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: question || "내 풀이 데이터를 분석해서 학습 계획을 세워줘",
                    guest_profile: guest_profile || {},
                    guest_logs: guest_logs || [],
                }),
                signal: AbortSignal.timeout(300000),
            });
            if (!response.ok) {
                const errorText = await response.text();
                return Response.json(
                    { success: false, error: "게스트 학습 계획 생성 실패", details: errorText },
                    { status: response.status }
                );
            }
            return Response.json(await response.json());
        }

        return Response.json(
            { error: "알 수 없는 action입니다." },
            { status: 400 }
        );
    } catch (error) {
        console.error("[API] study-plan 오류:", error);
        return Response.json(
            {
                error: "서버 오류가 발생했습니다.",
                details: error instanceof Error ? error.message : String(error),
            },
            { status: 500 }
        );
    }
}

