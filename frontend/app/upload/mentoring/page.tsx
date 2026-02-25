"use client";

import { useState, useRef, useCallback } from "react";

type UploadStatus = "idle" | "uploading" | "success" | "error";
type UploadResult = {
    success: boolean;
    filename: string;
    totalLines: number;
    insertedCount: number;
    duplicateCount: number;
    skippedCount: number;
    message: string;
    errors?: Array<{ line: number; error: string }>;
};

type EmbeddingStatus = {
    isComplete: boolean;
    totalCount: number;
    embeddedCount: number;
    remainingCount: number;
    progressPercent: number;
    message: string;
} | null;

type StatsData = {
    total: number;
    embeddedCount: number;
    intentDistribution: Array<{ intent: string; count: number }>;
} | null;

export default function MentoringUploadPage() {
    const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
    const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [stats, setStats] = useState<StatsData>(null);
    const [loadingStats, setLoadingStats] = useState(false);
    const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus>(null);
    const [embeddingLoading, setEmbeddingLoading] = useState(false);
    const [embeddingResult, setEmbeddingResult] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const handleFileUpload = async (file: File) => {
        if (!file.name.toLowerCase().endsWith(".jsonl")) {
            setUploadStatus("error");
            setUploadResult({
                success: false,
                filename: file.name,
                totalLines: 0,
                insertedCount: 0,
                duplicateCount: 0,
                skippedCount: 0,
                message: "",
                errors: [{ line: 0, error: "JSONL 파일만 업로드할 수 있습니다." }],
            });
            return;
        }

        setUploadStatus("uploading");
        setUploadResult(null);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const res = await fetch(
                `${backendUrl}/api/v1/admin/mentoring-knowledge/upload-jsonl`,
                { method: "POST", body: formData }
            );

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || err.error || `HTTP ${res.status}`);
            }

            const data = await res.json();
            const normalized: UploadResult = {
                success: !!data?.success,
                filename: data?.filename ?? file.name,
                totalLines: Number(data?.total_lines ?? 0),
                insertedCount: Number(data?.inserted_count ?? 0),
                duplicateCount: Number(data?.duplicate_count ?? 0),
                skippedCount: Number(data?.skipped_count ?? 0),
                message: data?.message ?? "",
                errors: Array.isArray(data?.errors) ? data.errors : undefined,
            };
            setUploadResult(normalized);
            setUploadStatus(normalized.success ? "success" : "error");

            // 성공 시 통계 갱신
            if (normalized.success) fetchStats();
        } catch (error) {
            setUploadStatus("error");
            setUploadResult({
                success: false,
                filename: file.name,
                totalLines: 0,
                insertedCount: 0,
                duplicateCount: 0,
                skippedCount: 0,
                message: "",
                errors: [
                    {
                        line: 0,
                        error: error instanceof Error ? error.message : "알 수 없는 오류",
                    },
                ],
            });
        }
    };

    const fetchStats = async () => {
        setLoadingStats(true);
        try {
            const res = await fetch(`${backendUrl}/api/v1/admin/mentoring-knowledge/stats`);
            if (res.ok) {
                const data = await res.json();
                setStats({
                    total: data.total ?? 0,
                    embeddedCount: data.embedded_count ?? 0,
                    intentDistribution: data.intent_distribution ?? [],
                });
            }
        } catch {
            /* ignore */
        } finally {
            setLoadingStats(false);
        }
    };

    const fetchEmbeddingStatus = async () => {
        try {
            const res = await fetch(`${backendUrl}/api/v1/admin/mentoring-knowledge/embedding-status`);
            if (res.ok) {
                const data = await res.json();
                setEmbeddingStatus({
                    isComplete: data.is_complete ?? false,
                    totalCount: data.total_count ?? 0,
                    embeddedCount: data.embedded_count ?? 0,
                    remainingCount: data.remaining_count ?? 0,
                    progressPercent: data.progress_percent ?? 0,
                    message: data.message ?? "",
                });
            }
        } catch {
            /* ignore */
        }
    };

    // 폴링 인터벌 ref
    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    const handleGenerateEmbeddings = async () => {
        setEmbeddingLoading(true);
        setEmbeddingResult(null);

        try {
            // 1) 백그라운드 임베딩 시작 요청 (즉시 응답)
            const res = await fetch(
                `${backendUrl}/api/v1/admin/mentoring-knowledge/enqueue-embeddings`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ batch_size: 50 }),
                }
            );

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }

            const data = await res.json();

            if (data.mode === "none") {
                setEmbeddingResult("✓ 임베딩이 필요한 데이터가 없습니다.");
                setEmbeddingLoading(false);
                return;
            }

            if (data.mode === "background_running") {
                setEmbeddingResult(`이미 진행 중: ${data.processed_count ?? 0}건 처리됨`);
            } else {
                setEmbeddingResult(
                    `백그라운드 임베딩 시작: ${(data.total_count ?? 0).toLocaleString()}건 처리 예정...`
                );
            }

            // 2) 진행 상황 폴링 시작 (3초 간격)
            if (pollingRef.current) clearInterval(pollingRef.current);

            pollingRef.current = setInterval(async () => {
                try {
                    const statusRes = await fetch(
                        `${backendUrl}/api/v1/admin/mentoring-knowledge/embedding-job-status`
                    );
                    if (!statusRes.ok) return;

                    const status = await statusRes.json();
                    const processed = status.processed ?? 0;
                    const total = status.total ?? 0;
                    const errors = status.errors ?? 0;
                    const elapsed = status.elapsed_seconds ?? 0;

                    // 임베딩 상태도 갱신
                    await fetchEmbeddingStatus();

                    if (status.running) {
                        const pct = total > 0 ? Math.round((processed / total) * 100) : 0;
                        const elapsedMin = Math.floor(elapsed / 60);
                        const elapsedSec = Math.round(elapsed % 60);
                        setEmbeddingResult(
                            `처리 중: ${processed.toLocaleString()}/${total.toLocaleString()}건 (${pct}%) ` +
                            `| 경과: ${elapsedMin}분 ${elapsedSec}초` +
                            (errors > 0 ? ` | 오류: ${errors}건` : "")
                        );
                    } else {
                        // 완료됨
                        if (pollingRef.current) {
                            clearInterval(pollingRef.current);
                            pollingRef.current = null;
                        }
                        setEmbeddingLoading(false);

                        if (processed > 0) {
                            setEmbeddingResult(
                                `✓ 완료! ${processed.toLocaleString()}건 임베딩 생성됨` +
                                (errors > 0 ? ` (${errors}건 실패)` : "")
                            );
                        } else {
                            setEmbeddingResult(status.message || "임베딩 작업이 종료되었습니다.");
                        }

                        // 통계 갱신
                        fetchEmbeddingStatus();
                        fetchStats();
                    }
                } catch {
                    // 폴링 오류는 무시 (다음 폴링에서 재시도)
                }
            }, 3000);

        } catch (error) {
            setEmbeddingResult(
                `오류: ${error instanceof Error ? error.message : "알 수 없는 오류"}`
            );
            setEmbeddingLoading(false);
        }
    };

    const handleStopEmbeddings = async () => {
        try {
            await fetch(
                `${backendUrl}/api/v1/admin/mentoring-knowledge/stop-embeddings`,
                { method: "POST" }
            );
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
                pollingRef.current = null;
            }
            setEmbeddingLoading(false);
            setEmbeddingResult("중단 요청됨. 현재 배치 완료 후 중단됩니다.");
            fetchEmbeddingStatus();
            fetchStats();
        } catch {
            setEmbeddingResult("중단 요청 실패");
        }
    };

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            e.stopPropagation();
            setIsDragging(false);

            const files = Array.from(e.dataTransfer.files);
            const jsonlFile = files.find((f) => f.name.toLowerCase().endsWith(".jsonl"));

            if (jsonlFile) {
                handleFileUpload(jsonlFile);
            } else {
                setUploadStatus("error");
                setUploadResult({
                    success: false,
                    filename: "",
                    totalLines: 0,
                    insertedCount: 0,
                    duplicateCount: 0,
                    skippedCount: 0,
                    message: "",
                    errors: [
                        {
                            line: 0,
                            error:
                                files.length === 0
                                    ? "파일이 인식되지 않았습니다."
                                    : "JSONL(.jsonl) 파일만 드롭할 수 있습니다.",
                        },
                    ],
                });
            }
        },
        // eslint-disable-next-line react-hooks/exhaustive-deps
        []
    );

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleFileUpload(file);
    };

    const resetUpload = () => {
        setUploadStatus("idle");
        setUploadResult(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    return (
        <div className="page-container">
            {/* 헤더 */}
            <div className="page-header">
                <h1 className="page-title">멘토링 지식 업로드</h1>
                <p className="page-desc">
                    merged_training_data.jsonl 파일을 업로드하여 합격 수기 기반 멘토링 Q&A 데이터를 저장합니다.
                </p>
            </div>

            {/* 드래그 앤 드롭 영역 */}
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`drop-zone ${isDragging ? "dragging" : ""}`}
            >
                <svg className="drop-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                    <polyline points="14 2 14 8 20 8" />
                </svg>
                <p className="drop-text">JSONL 파일을 여기에 드래그 앤 드롭하세요</p>
                <p className="drop-or">또는</p>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".jsonl"
                    onChange={handleFileSelect}
                    className="hidden-input"
                />
                <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="select-btn"
                >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" x2="12" y1="3" y2="15" />
                    </svg>
                    파일 선택
                </button>
                <p className="drop-hint">지원 형식: .jsonl (merged_training_data.jsonl)</p>
            </div>

            {/* 업로드 상태 */}
            {uploadStatus === "uploading" && (
                <div className="status-bar status-loading">
                    <span className="spinner" />
                    <span>파일을 업로드하고 있습니다... (4,911건 처리 중)</span>
                </div>
            )}

            {/* 업로드 결과 */}
            {uploadResult && (
                <div className={`result-card ${uploadStatus === "success" ? "result-success" : "result-error"}`}>
                    <div className="result-header">
                        <span className="result-icon">{uploadStatus === "success" ? "✓" : "✕"}</span>
                        <h4 className="result-title">
                            {uploadStatus === "success" ? "업로드 성공" : "업로드 실패"}
                        </h4>
                        <button className="close-btn" onClick={resetUpload}>✕</button>
                    </div>
                    <div className="result-body">
                        <p><span className="label">파일명</span> {uploadResult.filename}</p>
                        <p><span className="label">총 라인 수</span> {uploadResult.totalLines.toLocaleString()}</p>
                        {uploadResult.insertedCount > 0 && (
                            <p><span className="label">삽입 건수</span> {uploadResult.insertedCount.toLocaleString()}건</p>
                        )}
                        {uploadResult.duplicateCount > 0 && (
                            <p><span className="label">중복 스킵</span> <span style={{ color: '#f59e0b' }}>{uploadResult.duplicateCount.toLocaleString()}건 (이미 존재)</span></p>
                        )}
                        {uploadResult.skippedCount > 0 && (
                            <p><span className="label">오류 스킵</span> {uploadResult.skippedCount.toLocaleString()}건</p>
                        )}
                        {uploadResult.message && (
                            <p><span className="label">결과</span> {uploadResult.message}</p>
                        )}
                        {uploadResult.errors && uploadResult.errors.length > 0 && (
                            <div className="error-list">
                                <p className="error-list-title">오류 (상위 10개)</p>
                                {uploadResult.errors.map((err, idx) => (
                                    <p key={idx} className="error-item">라인 {err.line}: {err.error}</p>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 재업로드 */}
            {uploadStatus !== "idle" && uploadStatus !== "uploading" && (
                <div className="action-row">
                    <button className="outline-btn" onClick={resetUpload}>다시 업로드</button>
                </div>
            )}

            {/* 임베딩 생성 섹션 */}
            <div className="section-divider" />
            <div className="page-header">
                <h2 className="section-title">임베딩 생성</h2>
                <p className="page-desc">
                    멘토링 지식 데이터에 벡터 임베딩을 생성하여 RAG 유사도 검색을 활성화합니다.
                </p>
            </div>

            <div className="embedding-actions">
                <button
                    className={`action-btn ${embeddingLoading ? "disabled" : ""}`}
                    onClick={fetchEmbeddingStatus}
                    disabled={embeddingLoading}
                >
                    임베딩 상태 확인
                </button>
                {embeddingLoading ? (
                    <button
                        className="action-btn action-btn-danger"
                        onClick={handleStopEmbeddings}
                    >
                        ■ 중단
                    </button>
                ) : (
                    <button
                        className="action-btn action-btn-primary"
                        onClick={handleGenerateEmbeddings}
                    >
                        ✦ 임베딩 생성 (전체)
                    </button>
                )}
            </div>

            {embeddingStatus && (
                <div className="embedding-status-card">
                    <div className="embedding-progress-bar">
                        <div
                            className="embedding-progress-fill"
                            style={{ width: `${embeddingStatus.progressPercent}%` }}
                        />
                    </div>
                    <div className="embedding-stats-row">
                        <span className="embedding-stat">
                            전체: <strong>{embeddingStatus.totalCount.toLocaleString()}</strong>건
                        </span>
                        <span className="embedding-stat">
                            완료: <strong>{embeddingStatus.embeddedCount.toLocaleString()}</strong>건
                        </span>
                        <span className="embedding-stat">
                            남음: <strong>{embeddingStatus.remainingCount.toLocaleString()}</strong>건
                        </span>
                        <span className="embedding-stat">
                            진행률: <strong>{embeddingStatus.progressPercent}%</strong>
                        </span>
                    </div>
                    {embeddingStatus.isComplete && (
                        <p className="embedding-complete">✓ 모든 임베딩이 생성되었습니다.</p>
                    )}
                </div>
            )}

            {embeddingResult && (
                <div className={`embedding-result ${embeddingResult.startsWith("오류") ? "embedding-result-error" : "embedding-result-success"}`}>
                    {embeddingResult}
                </div>
            )}

            {/* 통계 섹션 */}
            <div className="section-divider" />
            <div className="page-header">
                <h2 className="section-title">데이터 통계</h2>
                <p className="page-desc">현재 저장된 멘토링 지식 통계입니다.</p>
            </div>

            <button
                className={`action-btn ${loadingStats ? "disabled" : ""}`}
                onClick={fetchStats}
                disabled={loadingStats}
            >
                {loadingStats ? (
                    <><span className="spinner" /> 통계 로딩 중...</>
                ) : (
                    <>통계 확인</>
                )}
            </button>

            {stats && (
                <div className="stats-card">
                    <div className="stats-grid">
                        <div className="stat-item">
                            <span className="stat-value">{stats.total.toLocaleString()}</span>
                            <span className="stat-label">전체 건수</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-value">{stats.embeddedCount.toLocaleString()}</span>
                            <span className="stat-label">임베딩 완료</span>
                        </div>
                    </div>
                    {stats.intentDistribution.length > 0 && (
                        <div className="intent-list">
                            <p className="intent-title">의도 분포</p>
                            {stats.intentDistribution.map((item, idx) => (
                                <div key={idx} className="intent-row">
                                    <span className="intent-name">{item.intent}</span>
                                    <span className="intent-count">{item.count.toLocaleString()}건</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            <style jsx>{`
                .page-container {
                    padding: 48px 40px;
                    max-width: 720px;
                    animation: fadeIn 0.5s ease-out;
                }

                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(12px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                .page-header { margin-bottom: 28px; }

                .page-title {
                    font-size: 1.5rem;
                    font-weight: 700;
                    color: rgba(255, 255, 255, 0.9);
                    letter-spacing: 0.02em;
                    margin: 0 0 8px 0;
                }

                .section-title {
                    font-size: 1.15rem;
                    font-weight: 600;
                    color: rgba(255, 255, 255, 0.8);
                    letter-spacing: 0.02em;
                    margin: 0 0 8px 0;
                }

                .page-desc {
                    font-size: 0.85rem;
                    color: rgba(255, 255, 255, 0.3);
                    margin: 0;
                    letter-spacing: 0.01em;
                }

                .drop-zone {
                    border: 1px dashed rgba(255, 255, 255, 0.1);
                    border-radius: 16px;
                    padding: 48px 24px;
                    text-align: center;
                    transition: all 0.3s ease;
                    background: rgba(255, 255, 255, 0.01);
                    margin-bottom: 20px;
                }

                .drop-zone.dragging {
                    border-color: rgba(255, 255, 255, 0.3);
                    background: rgba(255, 255, 255, 0.03);
                }

                .drop-zone:hover {
                    border-color: rgba(255, 255, 255, 0.15);
                }

                .drop-icon {
                    color: rgba(255, 255, 255, 0.15);
                    margin-bottom: 16px;
                }

                .drop-text {
                    font-size: 0.9rem;
                    color: rgba(255, 255, 255, 0.5);
                    margin: 0 0 8px 0;
                }

                .drop-or {
                    font-size: 0.75rem;
                    color: rgba(255, 255, 255, 0.2);
                    margin: 0 0 20px 0;
                }

                .hidden-input { display: none; }

                .select-btn {
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    padding: 10px 24px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    background: rgba(255, 255, 255, 0.04);
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 0.85rem;
                    font-family: inherit;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    letter-spacing: 0.05em;
                }

                .select-btn:hover {
                    background: rgba(255, 255, 255, 0.08);
                    color: rgba(255, 255, 255, 0.9);
                    border-color: rgba(255, 255, 255, 0.2);
                }

                .drop-hint {
                    font-size: 0.7rem;
                    color: rgba(255, 255, 255, 0.15);
                    margin: 16px 0 0 0;
                }

                .status-bar {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 14px 18px;
                    border-radius: 10px;
                    font-size: 0.8rem;
                    margin-bottom: 16px;
                }

                .status-loading {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    color: rgba(255, 255, 255, 0.5);
                }

                .spinner {
                    width: 14px;
                    height: 14px;
                    border: 2px solid rgba(255, 255, 255, 0.1);
                    border-top-color: rgba(255, 255, 255, 0.5);
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                }

                @keyframes spin {
                    to { transform: rotate(360deg); }
                }

                .result-card {
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 16px;
                }

                .result-success {
                    background: rgba(34, 197, 94, 0.06);
                    border: 1px solid rgba(34, 197, 94, 0.15);
                }

                .result-error {
                    background: rgba(239, 68, 68, 0.06);
                    border: 1px solid rgba(239, 68, 68, 0.15);
                }

                .result-header {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-bottom: 16px;
                }

                .result-icon {
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.75rem;
                    font-weight: 700;
                }

                .result-success .result-icon {
                    background: rgba(34, 197, 94, 0.15);
                    color: rgba(34, 197, 94, 0.9);
                }

                .result-error .result-icon {
                    background: rgba(239, 68, 68, 0.15);
                    color: rgba(239, 68, 68, 0.9);
                }

                .result-title {
                    flex: 1;
                    font-size: 0.9rem;
                    font-weight: 600;
                    margin: 0;
                }

                .result-success .result-title { color: rgba(34, 197, 94, 0.9); }
                .result-error .result-title { color: rgba(239, 68, 68, 0.9); }

                .close-btn {
                    width: 28px;
                    height: 28px;
                    border: none;
                    border-radius: 6px;
                    background: transparent;
                    color: rgba(255, 255, 255, 0.3);
                    cursor: pointer;
                    font-size: 0.75rem;
                    transition: all 0.2s ease;
                }

                .close-btn:hover {
                    background: rgba(255, 255, 255, 0.05);
                    color: rgba(255, 255, 255, 0.7);
                }

                .result-body p {
                    font-size: 0.8rem;
                    color: rgba(255, 255, 255, 0.5);
                    margin: 0 0 6px 0;
                }

                .label {
                    color: rgba(255, 255, 255, 0.7);
                    font-weight: 500;
                    margin-right: 8px;
                }

                .error-list {
                    margin-top: 12px;
                    padding: 12px;
                    background: rgba(239, 68, 68, 0.05);
                    border-radius: 8px;
                }

                .error-list-title {
                    font-size: 0.75rem;
                    font-weight: 600;
                    color: rgba(239, 68, 68, 0.7) !important;
                    margin-bottom: 8px !important;
                }

                .error-item {
                    font-size: 0.75rem !important;
                    color: rgba(239, 68, 68, 0.6) !important;
                }

                .action-row {
                    display: flex;
                    justify-content: flex-end;
                    margin-bottom: 16px;
                }

                .outline-btn {
                    padding: 8px 20px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    background: transparent;
                    color: rgba(255, 255, 255, 0.5);
                    font-size: 0.8rem;
                    font-family: inherit;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    letter-spacing: 0.03em;
                }

                .outline-btn:hover {
                    background: rgba(255, 255, 255, 0.04);
                    color: rgba(255, 255, 255, 0.8);
                    border-color: rgba(255, 255, 255, 0.2);
                }

                .action-btn {
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    padding: 12px 28px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    background: rgba(255, 255, 255, 0.04);
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 0.85rem;
                    font-family: inherit;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    letter-spacing: 0.05em;
                    margin-bottom: 16px;
                }

                .action-btn:hover:not(.disabled) {
                    background: rgba(255, 255, 255, 0.08);
                    color: rgba(255, 255, 255, 0.9);
                    border-color: rgba(255, 255, 255, 0.2);
                }

                .action-btn.disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .embedding-actions {
                    display: flex;
                    gap: 12px;
                    margin-bottom: 16px;
                }

                .action-btn-primary {
                    background: rgba(99, 102, 241, 0.12) !important;
                    border-color: rgba(99, 102, 241, 0.25) !important;
                    color: rgba(165, 168, 255, 0.9) !important;
                }

                .action-btn-primary:hover:not(.disabled) {
                    background: rgba(99, 102, 241, 0.2) !important;
                    border-color: rgba(99, 102, 241, 0.4) !important;
                    color: rgba(200, 202, 255, 1) !important;
                }

                .action-btn-danger {
                    background: rgba(239, 68, 68, 0.12) !important;
                    border-color: rgba(239, 68, 68, 0.25) !important;
                    color: rgba(255, 150, 150, 0.9) !important;
                }

                .action-btn-danger:hover {
                    background: rgba(239, 68, 68, 0.2) !important;
                    border-color: rgba(239, 68, 68, 0.4) !important;
                    color: rgba(255, 180, 180, 1) !important;
                }

                .embedding-status-card {
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 12px;
                    padding: 20px;
                    background: rgba(255, 255, 255, 0.02);
                    margin-bottom: 16px;
                }

                .embedding-progress-bar {
                    height: 6px;
                    border-radius: 3px;
                    background: rgba(255, 255, 255, 0.06);
                    overflow: hidden;
                    margin-bottom: 16px;
                }

                .embedding-progress-fill {
                    height: 100%;
                    border-radius: 3px;
                    background: linear-gradient(90deg, rgba(99, 102, 241, 0.6), rgba(139, 92, 246, 0.6));
                    transition: width 0.5s ease;
                }

                .embedding-stats-row {
                    display: flex;
                    gap: 24px;
                    flex-wrap: wrap;
                }

                .embedding-stat {
                    font-size: 0.8rem;
                    color: rgba(255, 255, 255, 0.4);
                }

                .embedding-stat strong {
                    color: rgba(255, 255, 255, 0.8);
                    font-weight: 600;
                }

                .embedding-complete {
                    margin: 12px 0 0 0;
                    font-size: 0.8rem;
                    color: rgba(34, 197, 94, 0.8);
                    font-weight: 500;
                }

                .embedding-result {
                    padding: 12px 18px;
                    border-radius: 10px;
                    font-size: 0.8rem;
                    margin-bottom: 16px;
                }

                .embedding-result-success {
                    background: rgba(34, 197, 94, 0.06);
                    border: 1px solid rgba(34, 197, 94, 0.15);
                    color: rgba(34, 197, 94, 0.9);
                }

                .embedding-result-error {
                    background: rgba(239, 68, 68, 0.06);
                    border: 1px solid rgba(239, 68, 68, 0.15);
                    color: rgba(239, 68, 68, 0.9);
                }

                .section-divider {
                    height: 1px;
                    background: rgba(255, 255, 255, 0.04);
                    margin: 36px 0;
                }

                .stats-card {
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 12px;
                    padding: 20px;
                    background: rgba(255, 255, 255, 0.02);
                }

                .stats-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 16px;
                    margin-bottom: 16px;
                }

                .stat-item {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    padding: 16px;
                    border-radius: 10px;
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.04);
                }

                .stat-value {
                    font-size: 1.5rem;
                    font-weight: 700;
                    color: rgba(255, 255, 255, 0.8);
                }

                .stat-label {
                    font-size: 0.75rem;
                    color: rgba(255, 255, 255, 0.3);
                    margin-top: 4px;
                }

                .intent-list {
                    margin-top: 16px;
                    padding-top: 16px;
                    border-top: 1px solid rgba(255, 255, 255, 0.04);
                }

                .intent-title {
                    font-size: 0.8rem;
                    font-weight: 600;
                    color: rgba(255, 255, 255, 0.5);
                    margin: 0 0 12px 0;
                }

                .intent-row {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 12px;
                    border-radius: 6px;
                    margin-bottom: 4px;
                }

                .intent-row:hover {
                    background: rgba(255, 255, 255, 0.02);
                }

                .intent-name {
                    font-size: 0.8rem;
                    color: rgba(255, 255, 255, 0.6);
                }

                .intent-count {
                    font-size: 0.8rem;
                    color: rgba(255, 255, 255, 0.4);
                    font-weight: 500;
                }
            `}</style>
        </div>
    );
}

