"use client";

import { useState, useRef, useCallback } from "react";

type UploadStatus = "idle" | "uploading" | "success" | "error";
type UploadResult = {
    success: boolean;
    message: string;
    totalItems?: number;
    insertedExams?: number;
    insertedQuestions?: number;
    insertedImages?: number;
    skippedImages?: number;
    errors?: Array<{ index: number; error: string }>;
};

export default function QuestionImageUploadPage() {
    const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
    const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileUpload = async (file: File) => {
        if (!file.name.toLowerCase().endsWith(".json")) {
            setUploadStatus("error");
            setUploadResult({
                success: false,
                message: "JSON 파일만 업로드할 수 있습니다.",
                errors: [{ index: 0, error: "crop_results.json 형식의 JSON 파일만 업로드할 수 있습니다." }],
            });
            return;
        }

        setUploadStatus("uploading");
        setUploadResult(null);

        try {
            const text = await file.text();
            const cropData = JSON.parse(text);

            if (!Array.isArray(cropData)) {
                throw new Error("JSON 파일은 배열 형식이어야 합니다.");
            }

            const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const uploadUrl = `${backendUrl}/api/v1/admin/questions/upload-crop-results`;

            const res = await fetch(uploadUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    crop_results: cropData,
                    filename: file.name,
                }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || err.error || `HTTP ${res.status}`);
            }

            const data = await res.json();
            const normalized: UploadResult = {
                success: !!data?.success,
                message: data?.message || "처리 완료",
                totalItems: data?.total_items,
                insertedExams: data?.inserted_exams,
                insertedQuestions: data?.inserted_questions,
                insertedImages: data?.inserted_images,
                skippedImages: data?.skipped_images,
                errors: Array.isArray(data?.errors) ? data.errors : undefined,
            };
            setUploadResult(normalized);
            setUploadStatus(normalized.success ? "success" : "error");
        } catch (error) {
            setUploadStatus("error");
            setUploadResult({
                success: false,
                message: error instanceof Error ? error.message : "알 수 없는 오류",
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
            const jsonFile = files.find((f) => f.name.toLowerCase().endsWith(".json"));

            if (jsonFile) {
                handleFileUpload(jsonFile);
            } else {
                setUploadStatus("error");
                setUploadResult({
                    success: false,
                    message: files.length === 0
                        ? "파일이 인식되지 않았습니다."
                        : "JSON(.json) 파일만 드롭할 수 있습니다.",
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
                <h1 className="page-title">문제 이미지 업로드</h1>
                <p className="page-desc">
                    YOLO로 크롭된 문제 이미지 메타데이터(crop_results.json)를 업로드하여<br />
                    시험 · 문제 · 이미지 데이터를 Neon DB에 저장합니다.
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
                    <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                    <circle cx="9" cy="9" r="2" />
                    <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
                </svg>
                <p className="drop-text">crop_results.json 파일을 여기에 드래그 앤 드롭하세요</p>
                <p className="drop-or">또는</p>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json"
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
                <p className="drop-hint">지원 형식: .json (crop_results.json)</p>
            </div>

            {/* 데이터 흐름 안내 */}
            <div className="info-card">
                <div className="info-title">📋 데이터 흐름</div>
                <div className="info-steps">
                    <div className="info-step">
                        <span className="step-num">1</span>
                        <span className="step-text">폴더명에서 시험 정보 파싱 (연도, 유형, 급, 과목)</span>
                    </div>
                    <div className="info-step">
                        <span className="step-num">2</span>
                        <span className="step-text">exams 테이블에 시험 레코드 생성/조회</span>
                    </div>
                    <div className="info-step">
                        <span className="step-num">3</span>
                        <span className="step-text">questions 테이블에 문제 레코드 생성/조회</span>
                    </div>
                    <div className="info-step">
                        <span className="step-num">4</span>
                        <span className="step-text">question_images 테이블에 이미지 레코드 저장 (bbox 좌표 포함)</span>
                    </div>
                </div>
            </div>

            {/* 업로드 상태 */}
            {uploadStatus === "uploading" && (
                <div className="status-bar status-loading">
                    <span className="spinner" />
                    <span>데이터를 처리하고 있습니다...</span>
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
                        <p><span className="label">메시지</span> {uploadResult.message}</p>
                        {uploadResult.totalItems !== undefined && (
                            <p><span className="label">총 항목</span> {uploadResult.totalItems}개</p>
                        )}
                        {uploadResult.insertedExams !== undefined && (
                            <p><span className="label">시험 생성</span> {uploadResult.insertedExams}개</p>
                        )}
                        {uploadResult.insertedQuestions !== undefined && (
                            <p><span className="label">문제 생성</span> {uploadResult.insertedQuestions}개</p>
                        )}
                        {uploadResult.insertedImages !== undefined && (
                            <p><span className="label">이미지 저장</span> {uploadResult.insertedImages}개</p>
                        )}
                        {uploadResult.skippedImages !== undefined && uploadResult.skippedImages > 0 && (
                            <p><span className="label">중복 건너뜀</span> {uploadResult.skippedImages}개</p>
                        )}
                        {uploadResult.errors && uploadResult.errors.length > 0 && (
                            <div className="error-list">
                                <p className="error-list-title">오류 ({uploadResult.errors.length}건)</p>
                                {uploadResult.errors.slice(0, 10).map((err, idx) => (
                                    <p key={idx} className="error-item">항목 {err.index}: {err.error}</p>
                                ))}
                                {uploadResult.errors.length > 10 && (
                                    <p className="error-item">... 외 {uploadResult.errors.length - 10}건</p>
                                )}
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
                    line-height: 1.6;
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

                .info-card {
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 20px;
                }

                .info-title {
                    font-size: 0.85rem;
                    font-weight: 600;
                    color: rgba(255, 255, 255, 0.6);
                    margin-bottom: 16px;
                }

                .info-steps {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }

                .info-step {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }

                .step-num {
                    width: 22px;
                    height: 22px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.06);
                    color: rgba(255, 255, 255, 0.4);
                    font-size: 0.7rem;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-shrink: 0;
                }

                .step-text {
                    font-size: 0.78rem;
                    color: rgba(255, 255, 255, 0.35);
                    letter-spacing: 0.01em;
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

