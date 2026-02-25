// Next.js Route Segment Config — 멘토링 RAG + EXAONE 생성 시간 고려
export const maxDuration = 120; // 2분
export const dynamic = "force-dynamic";

type ChatRequest = {
  question: string;
  // backend ChatRequest와 동일하게 graph 모드까지 지원
  mode?: "rag" | "openai" | "rag_openai" | "rag_local" | "local" | "graph";
  thread_id?: string;
};

type ChatResponse = {
  answer: string;
  retrieved_docs?: string[] | null;
  mode?: string;
  koelectra?: {
    gateway?: string | null;
    confidence?: number | null;
    method?: string | null;
  } | null;
};

export async function POST(request: Request) {
  try {
    const body: ChatRequest = await request.json();
    const { question, mode = "rag_openai", thread_id } = body;

    // 브라우저에서 받은 쿠키를 백엔드로 전달 (JWT 인증용)
    const cookieHeader = request.headers.get("cookie") || "";

    if (!question || !question.trim()) {
      return Response.json(
        { error: "질문이 비어있습니다." },
        { status: 400 }
      );
    }

    // Python 백엔드 RAG API 호출
    // 로컬 개발: .env.local에서 NEXT_PUBLIC_API_URL=http://localhost:8000 설정
    // Vercel 배포: Dashboard → Settings → Environment Variables에서 설정 필수
    // 오타 대응: NEXT_PUPLIC_API_URL도 체크
    const backendUrl =
      process.env.NEXT_PUBLIC_API_URL ||
      process.env.NEXT_PUPLIC_API_URL ||
      "http://localhost:8000";

    // 디버깅을 위한 로그 (민감 정보 은닉)
    const hasEnvVar = !!(process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUPLIC_API_URL);
    console.log("[Next.js API] 환경 변수 설정 여부:", hasEnvVar ? "✅ 설정됨" : "❌ 미설정");
    console.log("[Next.js API] 백엔드 URL 사용 중:", backendUrl.includes("localhost") ? "localhost (로컬)" : "프로덕션 URL");

    // Vercel 배포 환경에서 localhost 사용 시 경고
    if (backendUrl.includes("localhost") && process.env.VERCEL) {
      console.error("[Next.js API] ⚠️ 경고: Vercel 배포 환경에서 localhost를 사용하고 있습니다!");
      console.error("[Next.js API] Vercel Dashboard → Settings → Environment Variables에서 NEXT_PUBLIC_API_URL을 설정해주세요.");
    }

    console.log("[Next.js API] 요청 모드:", mode);
    console.log("[Next.js API] 요청 질문:", question.substring(0, 50) + "...");

    // 이제 exam 여부 판단은 모두 백엔드 ChatFlow에서 수행
    const requestUrl = `${backendUrl}/api/chat`;
    console.log("[Next.js API] 요청 URL 구성:", requestUrl);

    try {
      console.log("[Next.js API] 백엔드로 요청 시작...");
      const response = await fetch(requestUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(cookieHeader ? { Cookie: cookieHeader } : {}),
        },
        body: JSON.stringify({ question: question.trim(), mode, thread_id }),
        // 타임아웃 설정 (120초 - 멘토링 RAG + EXAONE 생성 시간 고려)
        signal: AbortSignal.timeout(120000),
      });

      console.log("[Next.js API] 응답 상태:", response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("[Next.js API] 백엔드 오류:", {
          status: response.status,
          statusText: response.statusText,
          error: errorText,
        });
        return Response.json(
          {
            error: "백엔드 서버에서 오류가 발생했습니다.",
            details: errorText,
            status: response.status,
          },
          { status: response.status }
        );
      }

      const data: ChatResponse = await response.json();
      console.log("[Next.js API] 응답 성공");
      return Response.json(data);
    } catch (fetchError) {
      // fetch 자체가 실패한 경우 (네트워크 오류, 타임아웃 등)
      const errorMessage = fetchError instanceof Error ? fetchError.message : String(fetchError);
      const errorName = fetchError instanceof Error ? fetchError.name : "Unknown";

      console.error("[Next.js API] 백엔드 연결 실패:", {
        error: errorMessage,
        name: errorName,
        requestUrl: requestUrl, // 디버깅을 위해 URL 포함
        backendUrl: backendUrl, // 디버깅을 위해 URL 포함
      });

      // 타임아웃 에러인지 확인
      if (errorName === "TimeoutError" || errorMessage.includes("timeout")) {
        console.error("[Next.js API] 타임아웃: 백엔드 서버가 120초 내에 응답하지 않았습니다.");
      }

      return Response.json(
        {
          error: "백엔드 서버에 연결할 수 없습니다.",
          details: errorMessage,
          errorType: errorName,
        },
        { status: 503 }
      );
    }
  } catch (error) {
    console.error("[Next.js API] /api/chat 오류:", {
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    return Response.json(
      {
        error: "서버 오류가 발생했습니다.",
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}

