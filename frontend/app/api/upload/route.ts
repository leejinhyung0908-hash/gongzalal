import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
    try {
        const formData = await request.formData();
        const file = formData.get("file") as File;
        const category = formData.get("category") as string | null;

        if (!file) {
            return NextResponse.json(
                { error: "파일이 제공되지 않았습니다." },
                { status: 400 }
            );
        }

        // JSONL 파일인지 확인
        if (!file.name.endsWith(".jsonl")) {
            return NextResponse.json(
                { error: "JSONL 파일만 업로드할 수 있습니다." },
                { status: 400 }
            );
        }

        // 파일 내용 읽기
        const text = await file.text();
        const lines = text.split("\n").filter((line) => line.trim());

        // 각 라인을 JSON으로 파싱
        const items = [];
        const errors = [];

        for (let i = 0; i < lines.length; i++) {
            try {
                const item = JSON.parse(lines[i]);
                items.push(item);
            } catch (error) {
                errors.push({
                    line: i + 1,
                    error: error instanceof Error ? error.message : "Unknown error",
                });
            }
        }

        // 처리 결과 반환
        return NextResponse.json({
            success: true,
            filename: file.name,
            category: category || "unknown",
            totalLines: lines.length,
            parsedItems: items.length,
            errors: errors.length > 0 ? errors : undefined,
            items: items, // 실제 사용 시에는 items를 DB에 저장하거나 처리
        });
    } catch (error) {
        console.error("파일 업로드 오류:", error);
        return NextResponse.json(
            {
                error: "파일 업로드 중 오류가 발생했습니다.",
                details: error instanceof Error ? error.message : "Unknown error",
            },
            { status: 500 }
        );
    }
}

