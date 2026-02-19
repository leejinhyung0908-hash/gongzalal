"use client";

import { useState, useRef, useCallback } from "react";

type UploadStatus = "idle" | "uploading" | "success" | "error";
type UploadResult = {
    success: boolean;
    filename: string;
    totalLines: number;
    parsedItems: number;
    errors?: Array<{ line: number; error: string }>;
};

export default function UserUploadPage() {
    const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
    const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileUpload = async (file: File) => {
        if (!file.name.toLowerCase().endsWith(".jsonl")) {
            setUploadStatus("error");
            setUploadResult({
                success: false,
                filename: file.name,
                totalLines: 0,
                parsedItems: 0,
                errors: [{ line: 0, error: "JSONL 파일만 업로드할 수 있습니다." }],
            });
            return;
        }

        setUploadStatus("uploading");
        setUploadResult(null);

        try {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("category", "user");

            const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const uploadUrl = `${backendUrl}/api/v1/admin/exam/upload-jsonl`;

            const res = await fetch(uploadUrl, {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || `HTTP ${res.status}`);
            }

            const data = await res.json();
            const normalized: UploadResult = {
                success: !!data?.success,
                filename: data?.filename ?? file.name,
                totalLines: Number(data?.total_lines ?? data?.totalLines ?? 0),
                parsedItems: Array.isArray(data?.parsed_items)
                    ? data.parsed_items.length
                    : Number(data?.parsedItems ?? 0),
                errors: Array.isArray(data?.errors) ? data.errors : undefined,
            };
            setUploadResult(normalized);
            setUploadStatus(normalized.success ? "success" : "error");
        } catch (error) {
            setUploadStatus("error");
            setUploadResult({
                success: false,
                filename: file.name,
                totalLines: 0,
                parsedItems: 0,
                errors: [
                    {
                        line: 0,
                        error: error instanceof Error ? error.message : "알 수 없는 오류",
                    },
                ],
            });
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
                    parsedItems: 0,
                    errors: [
                        {
                            line: 0,
                            error:
                                files.length === 0
                                    ? "파일이 인식되지 않았습니다. 탐색기에서 JSONL 파일을 드래그해서 놓아주세요."
                                    : "JSONL(.jsonl) 파일만 드롭할 수 있습니다.",
                        },
                    ],
                });
            }
        },
        []
    );

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleFileUpload(file);
        }
    };

    const resetUpload = () => {
        setUploadStatus("idle");
        setUploadResult(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    return (
        <div className="page-container">
            {/* 헤더 */}
            <div className="page-header">
                <h1 className="page-title">사용자 파일 업로드</h1>
                <p className="page-desc">
                    JSONL 파일을 드래그 앤 드롭하거나 파일을 선택하여 업로드하세요.
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
                <p className="drop-hint">지원 형식: .jsonl</p>
            </div>

            {/* 업로드 상태 */}
            {uploadStatus === "uploading" && (
                <div className="status-bar status-loading">
                    <span className="spinner" />
                    <span>파일을 업로드하고 있습니다...</span>
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
                        <p><span className="label">총 라인 수</span> {uploadResult.totalLines}</p>
                        <p><span className="label">파싱된 항목</span> {uploadResult.parsedItems}</p>
                        {uploadResult.errors && uploadResult.errors.length > 0 && (
                            <div className="error-list">
                                <p className="error-list-title">오류</p>
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

                .drop-zone:hover { border-color: rgba(255, 255, 255, 0.15); }

                .drop-icon { color: rgba(255, 255, 255, 0.15); margin-bottom: 16px; }

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

                @keyframes spin { to { transform: rotate(360deg); } }

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

                .result-success .result-icon { background: rgba(34, 197, 94, 0.15); color: rgba(34, 197, 94, 0.9); }
                .result-error .result-icon { background: rgba(239, 68, 68, 0.15); color: rgba(239, 68, 68, 0.9); }

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
            `}</style>
        </div>
    );
}
