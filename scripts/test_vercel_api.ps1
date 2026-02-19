# Vercel API 테스트 스크립트 (PowerShell)

Write-Host "🔍 Vercel API 테스트" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host ""

# Vercel 프로젝트 URL (실제 URL로 변경)
$vercelUrl = "https://rag-nine-cyan.vercel.app"

Write-Host "📍 Vercel URL: $vercelUrl" -ForegroundColor Yellow
Write-Host ""

# 테스트 요청
Write-Host "1️⃣ API 요청 전송 중..." -ForegroundColor Cyan

try {
    $body = @{
        question = "테스트 메시지"
        mode = "rag_openai"
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "$vercelUrl/api/chat" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -UseBasicParsing

    Write-Host "✅ 요청 성공!" -ForegroundColor Green
    Write-Host "상태 코드: $($response.StatusCode)" -ForegroundColor Green
    Write-Host ""
    Write-Host "응답 내용:" -ForegroundColor Yellow
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
}
catch {
    Write-Host "❌ 요청 실패!" -ForegroundColor Red
    Write-Host ""
    Write-Host "오류 메시지:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""

    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "상태 코드: $statusCode" -ForegroundColor Red

        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host "응답 본문:" -ForegroundColor Red
            Write-Host $responseBody -ForegroundColor Red
        }
        catch {
            Write-Host "응답 본문을 읽을 수 없습니다." -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "===================" -ForegroundColor Cyan
Write-Host "✅ 테스트 완료" -ForegroundColor Green
