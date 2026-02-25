"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { useUser } from "@/lib/hooks/useUser";

// ── 타입 ──
type MappedQuestion = {
    question_id: number;
    question_no: number;
    answer_key: string | null;
};

type QuestionImage = {
    image_id: number;
    question_id: number;
    file_path: string;
    coordinates_json: Record<string, any>;
    image_type: string;
    question_no: number;
    question_nos?: number[];
    mapped_questions?: MappedQuestion[];
    answer_key: string | null;
    exam_id: number;
    year: number;
    exam_type: string;
    subject: string;
    grade: string | null;
    series: string | null;
};

// ── 펜 색상 프리셋 ──
const PEN_COLORS = [
    { id: "red", color: "#ff3b3b", label: "빨강" },
    { id: "blue", color: "#3b82f6", label: "파랑" },
    { id: "green", color: "#22c55e", label: "초록" },
    { id: "yellow", color: "#facc15", label: "노랑" },
];

// ── 파티클 데이터 (hydration 일치) ──
const PARTICLES = [
    { left: "5%", delay: "0s", duration: "7s", opacity: 0.2 },
    { left: "15%", delay: "4s", duration: "11s", opacity: 0.18 },
    { left: "28%", delay: "5s", duration: "10s", opacity: 0.35 },
    { left: "38%", delay: "7s", duration: "7.5s", opacity: 0.28 },
    { left: "48%", delay: "6s", duration: "8.5s", opacity: 0.32 },
    { left: "58%", delay: "4.5s", duration: "13s", opacity: 0.26 },
    { left: "68%", delay: "7.5s", duration: "10s", opacity: 0.2 },
    { left: "77%", delay: "5.5s", duration: "9s", opacity: 0.24 },
    { left: "86%", delay: "6.5s", duration: "7.8s", opacity: 0.33 },
    { left: "94%", delay: "4.2s", duration: "9.2s", opacity: 0.27 },
];

function formatTime(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatQuestionNos(image: QuestionImage, fallbackNo: number): string {
    if (Array.isArray(image.question_nos) && image.question_nos.length > 0) {
        const nums = image.question_nos
            .map((n) => Number(n))
            .filter((n) => Number.isInteger(n) && n > 0);
        if (nums.length > 0) return Array.from(new Set(nums)).join(", ");
    }
    if (Number.isInteger(image.question_no) && image.question_no > 0) {
        return String(image.question_no);
    }
    return String(fallbackNo);
}

function getMappedQuestions(image: QuestionImage): MappedQuestion[] {
    if (Array.isArray(image.mapped_questions) && image.mapped_questions.length > 0) {
        return image.mapped_questions;
    }
    return [{
        question_id: image.question_id,
        question_no: image.question_no,
        answer_key: image.answer_key,
    }];
}

function getPrimaryMappedQuestion(image: QuestionImage): MappedQuestion {
    return getMappedQuestions(image)[0];
}

function formatMappedAnswerKey(image: QuestionImage): string {
    const mapped = getMappedQuestions(image);
    if (mapped.length <= 1) return mapped[0]?.answer_key ?? "미정";
    return mapped
        .map((q) => `${q.question_no}번:${q.answer_key ?? "미정"}`)
        .join(" / ");
}

function formatMappedSelectedAnswers(
    image: QuestionImage,
    selectedByQuestionId: Record<number, number | null>,
): string {
    const mapped = getMappedQuestions(image);
    if (mapped.length <= 1) {
        const selected = selectedByQuestionId[mapped[0]?.question_id ?? -1];
        return selected != null ? String(selected) : "-";
    }
    return mapped
        .map((q) => `${q.question_no}번:${selectedByQuestionId[q.question_id] ?? "-"}`)
        .join(" / ");
}

function classifyAnswer(selected: number | null, answerKey: string | null): "correct" | "wrong" | "unanswered" | "unknown" {
    if (!answerKey || answerKey === "미정") return "unknown";
    if (selected == null) return "unanswered";
    return String(selected) === String(answerKey) ? "correct" : "wrong";
}

export default function RandomExamPage() {
    // ── 로그인 사용자 ──
    const { user: loggedInUser } = useUser();
    const searchParams = useSearchParams();

    // ── 상태 ──
    const [images, setImages] = useState<QuestionImage[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // 타이머
    const [totalElapsed, setTotalElapsed] = useState(0);
    const [questionElapsed, setQuestionElapsed] = useState(0);
    const [isRunning, setIsRunning] = useState(false);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // 문제별 기록
    const [questionTimes, setQuestionTimes] = useState<number[]>([]);

    // 완료 상태
    const [isFinished, setIsFinished] = useState(false);

    // 리뷰 모드 (완료 후 문제 확인)
    const [isReviewing, setIsReviewing] = useState(false);
    const [reviewIndex, setReviewIndex] = useState(0);
    const [activeMappedQuestionNoByIndex, setActiveMappedQuestionNoByIndex] = useState<Record<number, number>>({});

    // 해설 상태
    const [commentaryMap, setCommentaryMap] = useState<Record<number, string | null>>({});
    const [commentaryLoading, setCommentaryLoading] = useState(false);
    const [showCommentary, setShowCommentary] = useState(false);

    // TTS 오디오 상태
    const [commentaryIdMap, setCommentaryIdMap] = useState<Record<number, number | null>>({});
    const [audioNoteMap, setAudioNoteMap] = useState<Record<number, { audioId: number; duration: number } | null>>({});
    const [generatingTTS, setGeneratingTTS] = useState<number | null>(null);
    const [playingQuestionId, setPlayingQuestionId] = useState<number | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    // 이미지 로딩
    const [imageLoaded, setImageLoaded] = useState(false);

    // ── 정답 선택 상태 (question_id 기준) ──
    const [selectedAnswersByQuestionId, setSelectedAnswersByQuestionId] = useState<Record<number, number | null>>({});

    // ── 풀이 기록 저장 상태 ──
    const [savingLogs, setSavingLogs] = useState(false);
    const [logsSaved, setLogsSaved] = useState(false);

    // ── 캔버스 드로잉 상태 ──
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const imgRef = useRef<HTMLImageElement>(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [penColor, setPenColor] = useState(PEN_COLORS[0].color);
    const [penSize, setPenSize] = useState(2.5);
    const [isEraser, setIsEraser] = useState(false);

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const mode = searchParams.get("mode");
    const selectedYear = searchParams.get("year");
    const selectedSubject = searchParams.get("subject");
    const selectedSeries = searchParams.get("series");
    const selectedCount = Number(searchParams.get("count") || "20");
    const isSelectMode = mode === "select";

    // ── 랜덤 문제 이미지 불러오기 ──
    const fetchRandomImages = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const isSelectRequestMode =
                isSelectMode &&
                !!selectedYear &&
                !!selectedSubject;

            const url = isSelectRequestMode
                ? `${backendUrl}/api/v1/admin/questions/images/select?year=${encodeURIComponent(selectedYear)}&subject=${encodeURIComponent(selectedSubject)}&series=${encodeURIComponent(selectedSeries || "")}&count=${Math.max(1, Math.min(selectedCount || 20, 100))}`
                : `${backendUrl}/api/v1/admin/questions/images/random?count=20`;

            const res = await fetch(url);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.success && data.images?.length > 0) {
                const incomingImages: QuestionImage[] = data.images;
                const initialSelectedMap: Record<number, number | null> = {};
                incomingImages.forEach((img) => {
                    getMappedQuestions(img).forEach((q) => {
                        initialSelectedMap[q.question_id] = null;
                    });
                });
                setImages(data.images);
                setCurrentIndex(0);
                setQuestionTimes(new Array(data.images.length).fill(0));
                setSelectedAnswersByQuestionId(initialSelectedMap);
                setTotalElapsed(0);
                setQuestionElapsed(0);
                setIsFinished(false);
                setIsRunning(true);
            } else {
                setError(
                    isSelectRequestMode
                        ? "선택한 조건에 맞는 문제가 없습니다. 조건을 바꿔 다시 시도해주세요."
                        : "등록된 문제 이미지가 없습니다. 먼저 crop_results.json을 업로드해주세요."
                );
            }
        } catch (e) {
            setError(e instanceof Error ? e.message : "문제 이미지를 불러오지 못했습니다.");
        } finally {
            setLoading(false);
        }
    }, [backendUrl, isSelectMode, selectedYear, selectedSubject, selectedSeries, selectedCount]);

    useEffect(() => {
        fetchRandomImages();
    }, [fetchRandomImages]);

    // ── 타이머 ──
    useEffect(() => {
        if (isRunning) {
            timerRef.current = setInterval(() => {
                setTotalElapsed((prev) => prev + 1);
                setQuestionElapsed((prev) => prev + 1);
            }, 1000);
        }
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [isRunning]);

    // ── 캔버스 초기화 (이미지 로드 시 & 문제 변경 시) ──
    const initCanvas = useCallback(() => {
        const canvas = canvasRef.current;
        const container = containerRef.current;
        const img = imgRef.current;
        if (!canvas || !container || !img) return;

        // 이미지의 실제 렌더링 크기에 맞춤
        const w = img.clientWidth;
        const h = img.clientHeight;

        // 고해상도 디스플레이 대응
        const dpr = window.devicePixelRatio || 1;
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = `${w}px`;
        canvas.style.height = `${h}px`;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.scale(dpr, dpr);
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
    }, []);

    // 이미지 로드 완료 시 캔버스 초기화
    const handleImageLoad = useCallback(() => {
        setImageLoaded(true);
        // 이미지 렌더링 후 캔버스 초기화 (약간의 딜레이)
        requestAnimationFrame(() => {
            initCanvas();
        });
    }, [initCanvas]);

    // 문제 변경 시 캔버스 클리어
    useEffect(() => {
        const canvas = canvasRef.current;
        if (canvas) {
            const ctx = canvas.getContext("2d");
            if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    }, [currentIndex]);

    // 리사이즈 대응
    useEffect(() => {
        const handleResize = () => {
            if (imageLoaded) initCanvas();
        };
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, [imageLoaded, initCanvas]);

    // ── 드로잉 로직 ──
    const getCoordinates = (e: React.MouseEvent | React.TouchEvent): { x: number; y: number } => {
        const canvas = canvasRef.current;
        if (!canvas) return { x: 0, y: 0 };
        const rect = canvas.getBoundingClientRect();
        const nativeEvent = e.nativeEvent;
        let clientX: number, clientY: number;
        if ("touches" in nativeEvent && nativeEvent.touches.length > 0) {
            clientX = nativeEvent.touches[0].clientX;
            clientY = nativeEvent.touches[0].clientY;
        } else if ("clientX" in nativeEvent) {
            clientX = (nativeEvent as MouseEvent).clientX;
            clientY = (nativeEvent as MouseEvent).clientY;
        } else {
            return { x: 0, y: 0 };
        }
        return { x: clientX - rect.left, y: clientY - rect.top };
    };

    const startDrawing = (e: React.MouseEvent | React.TouchEvent) => {
        const { x, y } = getCoordinates(e);
        const ctx = canvasRef.current?.getContext("2d");
        if (!ctx) return;
        ctx.beginPath();
        ctx.moveTo(x, y);

        if (isEraser) {
            ctx.globalCompositeOperation = "destination-out";
            ctx.lineWidth = penSize * 6;
        } else {
            ctx.globalCompositeOperation = "source-over";
            ctx.strokeStyle = penColor;
            ctx.lineWidth = penSize;
        }
        setIsDrawing(true);
    };

    const draw = (e: React.MouseEvent | React.TouchEvent) => {
        if (!isDrawing) return;
        // 모바일에서 터치 스크롤 방지
        if ("cancelable" in e && (e as any).cancelable) {
            e.preventDefault();
        }
        const { x, y } = getCoordinates(e);
        const ctx = canvasRef.current?.getContext("2d");
        if (!ctx) return;
        ctx.lineTo(x, y);
        ctx.stroke();
    };

    const stopDrawing = () => {
        if (isDrawing) {
            const ctx = canvasRef.current?.getContext("2d");
            if (ctx) ctx.globalCompositeOperation = "source-over";
            setIsDrawing(false);
        }
    };

    const clearCanvas = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    };

    // ── 정답 선택 ──
    const getSelectedAnswer = (questionId: number): number | null => {
        return selectedAnswersByQuestionId[questionId] ?? null;
    };

    const selectAnswer = (questionId: number, answerNum: number) => {
        setSelectedAnswersByQuestionId((prev) => ({
            ...prev,
            [questionId]: prev[questionId] === answerNum ? null : answerNum,
        }));
    };

    // ── 다음 문제 ──
    const goNext = () => {
        if (currentIndex >= images.length - 1) {
            const finalTimes = [...questionTimes];
            finalTimes[currentIndex] = questionElapsed;
            setQuestionTimes(finalTimes);
            setIsRunning(false);
            setIsFinished(true);
            // 풀이 기록 저장
            saveSolvingLogs(finalTimes);
            return;
        }
        setQuestionTimes((prev) => {
            const updated = [...prev];
            updated[currentIndex] = questionElapsed;
            return updated;
        });
        setQuestionElapsed(0);
        setImageLoaded(false);
        setCurrentIndex((prev) => prev + 1);
    };

    // ── 이전 문제 ──
    const goPrev = () => {
        if (currentIndex <= 0) return;
        setQuestionTimes((prev) => {
            const updated = [...prev];
            updated[currentIndex] = questionElapsed;
            return updated;
        });
        setQuestionElapsed(questionTimes[currentIndex - 1] || 0);
        setImageLoaded(false);
        setCurrentIndex((prev) => prev - 1);
    };

    // ── 풀이 기록 저장 ──
    const saveSolvingLogs = useCallback(async (
        finalQuestionTimes: number[],
    ) => {
        if (logsSaved || savingLogs || images.length === 0) return;
        setSavingLogs(true);
        try {
            const expandedLogs = images.flatMap((img, idx) => {
                const mapped = getMappedQuestions(img);
                const baseTime = finalQuestionTimes[idx] ?? 0;
                const perQuestionTime = Math.max(0, Math.round(baseTime / Math.max(mapped.length, 1)));
                return mapped.map((q) => {
                    const selected = getSelectedAnswer(q.question_id);
                    const status = classifyAnswer(selected, q.answer_key);
                    return {
                        question_id: q.question_id,
                        selected_answer: selected != null ? String(selected) : null,
                        time_spent: perQuestionTime,
                        is_wrong_note: status === "wrong",
                    };
                });
            });

            // 동일 question_id 중복 저장 방지 (마지막 값 우선)
            const logByQuestionId = new Map<number, {
                question_id: number;
                selected_answer: string | null;
                time_spent: number;
                is_wrong_note: boolean;
            }>();
            expandedLogs.forEach((log) => {
                logByQuestionId.set(log.question_id, log);
            });
            const logs = Array.from(logByQuestionId.values());

            const res = await fetch(`${backendUrl}/api/v1/admin/solving-logs/batch`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: loggedInUser?.id ?? 1, logs }),
            });

            if (res.ok) {
                const data = await res.json();
                console.log(`[SolvingLogs] ${data.inserted_count}건 저장 완료`);
                setLogsSaved(true);
            } else {
                console.error("[SolvingLogs] 저장 실패:", res.status, await res.text());
            }
        } catch (err) {
            console.error("[SolvingLogs] 저장 오류:", err);
        } finally {
            setSavingLogs(false);
        }
    }, [images, selectedAnswersByQuestionId, backendUrl, logsSaved, savingLogs]);

    // ── 다시 시작 ──
    const restart = () => {
        setIsReviewing(false);
        setReviewIndex(0);
        setLogsSaved(false);
        fetchRandomImages();
    };

    // ── 채점 결과 계산 ──
    const getGradingResults = () => {
        let correct = 0;
        let wrong = 0;
        let unanswered = 0;
        let unknown = 0; // answer_key가 "미정"인 경우

        images.forEach((img, idx) => {
            const mapped = getMappedQuestions(img);
            mapped.forEach((q) => {
                const selected = getSelectedAnswer(q.question_id);
                const status = classifyAnswer(selected, q.answer_key);
                if (status === "correct") correct++;
                else if (status === "wrong") wrong++;
                else if (status === "unanswered") unanswered++;
                else unknown++;
            });
        });

        const totalMappedQuestions = correct + wrong + unanswered + unknown;
        const gradable = totalMappedQuestions - unknown;
        const score = gradable > 0 ? Math.round((correct / gradable) * 100) : 0;

        return { correct, wrong, unanswered, unknown, score, gradable };
    };

    const getQuestionResult = (idx: number) => {
        const image = images[idx];
        if (!image) return "unknown";
        const mapped = getMappedQuestions(image);
        const statuses = mapped.map((q) => classifyAnswer(getSelectedAnswer(q.question_id), q.answer_key));

        if (statuses.includes("wrong")) return "wrong";
        if (statuses.includes("unanswered")) return "unanswered";
        if (statuses.includes("correct")) return "correct";
        return "unknown";
    };

    // ── 리뷰 모드 ──
    const startReview = (idx?: number) => {
        const targetIdx = idx ?? 0;
        const targetImage = images[targetIdx];
        const firstMappedQno = targetImage ? getMappedQuestions(targetImage)[0]?.question_no : undefined;
        setIsReviewing(true);
        setReviewIndex(targetIdx);
        if (firstMappedQno != null) {
            setActiveMappedQuestionNoByIndex((prev) => ({ ...prev, [targetIdx]: firstMappedQno }));
        }
        setImageLoaded(false);
    };

    const exitReview = () => {
        stopAudio();
        setIsReviewing(false);
        setShowCommentary(false);
    };

    const reviewPrev = () => {
        if (reviewIndex <= 0) return;
        stopAudio();
        const nextIndex = reviewIndex - 1;
        const nextImage = images[nextIndex];
        const firstMappedQno = nextImage ? getMappedQuestions(nextImage)[0]?.question_no : undefined;
        setImageLoaded(false);
        setShowCommentary(false);
        setReviewIndex(nextIndex);
        if (firstMappedQno != null) {
            setActiveMappedQuestionNoByIndex((prev) => ({ ...prev, [nextIndex]: firstMappedQno }));
        }
    };

    const reviewNext = () => {
        if (reviewIndex >= images.length - 1) return;
        stopAudio();
        const nextIndex = reviewIndex + 1;
        const nextImage = images[nextIndex];
        const firstMappedQno = nextImage ? getMappedQuestions(nextImage)[0]?.question_no : undefined;
        setImageLoaded(false);
        setShowCommentary(false);
        setReviewIndex(nextIndex);
        if (firstMappedQno != null) {
            setActiveMappedQuestionNoByIndex((prev) => ({ ...prev, [nextIndex]: firstMappedQno }));
        }
    };

    // 해설 가져오기
    const fetchCommentary = async (questionId: number) => {
        // 이미 로드된 경우 토글만
        if (questionId in commentaryMap) {
            setShowCommentary((prev) => !prev);
            return;
        }
        setCommentaryLoading(true);
        try {
            const res = await fetch(`${backendUrl}/api/v1/admin/commentaries/by-question/${questionId}`);
            if (res.ok) {
                const data = await res.json();
                setCommentaryMap((prev) => ({ ...prev, [questionId]: data.commentary?.body || null }));
                setCommentaryIdMap((prev) => ({ ...prev, [questionId]: data.commentary?.id ?? null }));
                setShowCommentary(true);
            } else {
                setCommentaryMap((prev) => ({ ...prev, [questionId]: null }));
                setCommentaryIdMap((prev) => ({ ...prev, [questionId]: null }));
                setShowCommentary(true);
            }
        } catch {
            setCommentaryMap((prev) => ({ ...prev, [questionId]: null }));
            setCommentaryIdMap((prev) => ({ ...prev, [questionId]: null }));
            setShowCommentary(true);
        } finally {
            setCommentaryLoading(false);
        }
    };

    // 해설 ID만 로드 (TTS 용, UI 토글 없음)
    const loadCommentaryId = async (questionId: number): Promise<number | null> => {
        if (questionId in commentaryIdMap) return commentaryIdMap[questionId];
        try {
            const res = await fetch(`${backendUrl}/api/v1/admin/commentaries/by-question/${questionId}`);
            if (res.ok) {
                const data = await res.json();
                const cId = data.commentary?.id ?? null;
                setCommentaryMap((prev) => ({ ...prev, [questionId]: data.commentary?.body || null }));
                setCommentaryIdMap((prev) => ({ ...prev, [questionId]: cId }));
                return cId;
            }
        } catch { /* ignore */ }
        setCommentaryIdMap((prev) => ({ ...prev, [questionId]: null }));
        return null;
    };

    // TTS 음성 생성 & 재생
    const handleTTSPlay = async (questionId: number) => {
        // 이미 재생 중이면 토글 (일시정지/재생)
        if (playingQuestionId === questionId && audioRef.current) {
            if (audioRef.current.paused) {
                audioRef.current.play();
            } else {
                audioRef.current.pause();
            }
            return;
        }

        // 1. commentary_id 가져오기
        const commentaryId = await loadCommentaryId(questionId);
        if (!commentaryId) {
            alert("해설이 등록되지 않은 문제입니다.");
            return;
        }

        // 2. 이미 생성된 오디오가 있으면 바로 재생
        const existing = audioNoteMap[questionId];
        if (existing) {
            playAudioById(existing.audioId, questionId);
            return;
        }

        // 3. TTS 생성 요청
        setGeneratingTTS(questionId);
        try {
            const res = await fetch(`${backendUrl}/api/v1/admin/audio-notes/generate-tts`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ commentary_id: commentaryId, voice_type: "female" }),
            });
            const data = await res.json();
            if (data.success && data.audio_note) {
                const audioInfo = {
                    audioId: data.audio_note.id,
                    duration: data.audio_note.duration || 0,
                };
                setAudioNoteMap((prev) => ({ ...prev, [questionId]: audioInfo }));
                playAudioById(audioInfo.audioId, questionId);
            } else {
                console.error("[TTS] 생성 실패:", data);
                alert("음성 생성에 실패했습니다.");
            }
        } catch (err) {
            console.error("[TTS] 요청 오류:", err);
            alert("음성 생성 중 오류가 발생했습니다.");
        } finally {
            setGeneratingTTS(null);
        }
    };

    // 오디오 재생
    const playAudioById = (audioId: number, questionId: number) => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current.src = `${backendUrl}/api/v1/admin/audio-notes/serve/${audioId}`;
            audioRef.current.load();
            audioRef.current.play().catch((err) => console.error("[TTS] 재생 오류:", err));
            setPlayingQuestionId(questionId);
        }
    };

    // 오디오 정지
    const stopAudio = () => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current.currentTime = 0;
        }
        setPlayingQuestionId(null);
    };

    // ── 현재 문제 ──
    const activeIndex = isReviewing ? reviewIndex : currentIndex;
    const currentImage = images[activeIndex] || null;
    const displayedQuestionNo = currentImage
        ? formatQuestionNos(currentImage, isSelectMode ? activeIndex + 1 : currentImage.question_no)
        : "";

    // ── 이미지 서빙 URL ──
    const imageUrl = currentImage
        ? `${backendUrl}/api/v1/admin/questions/images/serve/${currentImage.image_id}`
        : "";

    // 리뷰 모드에서의 현재 문제 결과
    const reviewResult = isReviewing ? getQuestionResult(reviewIndex) : null;
    const reviewImage = isReviewing ? images[reviewIndex] : null;
    const reviewMappedQuestions = reviewImage ? getMappedQuestions(reviewImage) : [];
    const activeReviewMappedQno = reviewMappedQuestions.length > 0
        ? (activeMappedQuestionNoByIndex[reviewIndex] ?? reviewMappedQuestions[0].question_no)
        : null;
    const activeReviewMappedQuestion = reviewMappedQuestions.find((q) => q.question_no === activeReviewMappedQno)
        ?? reviewMappedQuestions[0]
        ?? null;

    return (
        <div className="exam-container">
            {/* 배경 파티클 */}
            <div className="particles">
                {PARTICLES.map((p, i) => (
                    <span
                        key={i}
                        className="particle"
                        style={{
                            left: p.left,
                            animationDelay: p.delay,
                            animationDuration: p.duration,
                            opacity: p.opacity,
                        }}
                    />
                ))}
            </div>

            {/* 상단 로고 */}
            <a href="/" className="top-logo">
                <span>공</span><span>잘</span><span>알</span>
            </a>

            {/* 타이머 (우측 상단) */}
            <div className="timer-area">
                <div className="timer-total">
                    <span className="timer-label">총 시간</span>
                    <span className="timer-value">{formatTime(totalElapsed)}</span>
                </div>
                <div className="timer-question">
                    <span className="timer-label">문제 시간</span>
                    <span className="timer-value timer-value-accent">{formatTime(questionElapsed)}</span>
                </div>
            </div>

            {/* 메인 콘텐츠 */}
            <div className="content">
                {loading && (
                    <div className="state-message">
                        <div className="spinner" />
                        <p>문제를 불러오고 있습니다...</p>
                    </div>
                )}

                {error && !loading && (
                    <div className="state-message">
                        <p className="error-text">{error}</p>
                        <button className="action-btn" onClick={restart}>다시 시도</button>
                    </div>
                )}

                {!loading && !error && !isFinished && !isReviewing && currentImage && (
                    <>
                        {/* 문제 정보 바 */}
                        <div className="question-info">
                            <span className="q-number">{currentIndex + 1} / {images.length}</span>
                            <span className="q-meta">
                                {currentImage.year}년 {currentImage.exam_type} {currentImage.subject} {displayedQuestionNo}번
                            </span>
                        </div>

                        {/* 문제 이미지 + 정답 버튼 영역 */}
                        <div className="question-area">
                            {/* 왼쪽 정답 선택 버튼 */}
                            <div className="answer-panel">
                                <span className="answer-label">정답</span>
                                {getMappedQuestions(currentImage).map((mq) => (
                                    <div key={mq.question_id} className="answer-group">
                                        <span className="answer-sub-label">{mq.question_no}번</span>
                                        {[1, 2, 3, 4].map((num) => (
                                            <button
                                                key={`${mq.question_id}-${num}`}
                                                className={`answer-btn ${getSelectedAnswer(mq.question_id) === num ? "selected" : ""}`}
                                                onClick={() => selectAnswer(mq.question_id, num)}
                                            >
                                                {num}
                                            </button>
                                        ))}
                                    </div>
                                ))}
                            </div>

                            {/* 이미지 + 캔버스 오버레이 */}
                            <div ref={containerRef} className="image-wrapper">
                                {!imageLoaded && (
                                    <div className="image-loading">
                                        <div className="spinner" />
                                    </div>
                                )}
                                <img
                                    ref={imgRef}
                                    key={currentImage.image_id}
                                    src={imageUrl}
                                    alt={`문제 ${currentImage.question_no}`}
                                    className={`question-image ${imageLoaded ? "loaded" : ""}`}
                                    onLoad={handleImageLoad}
                                    onError={() => setImageLoaded(true)}
                                    draggable={false}
                                />
                                {/* OHP 캔버스 (이미지 위에 겹침) */}
                                {imageLoaded && (
                                    <canvas
                                        ref={canvasRef}
                                        className="draw-canvas"
                                        onMouseDown={startDrawing}
                                        onMouseMove={draw}
                                        onMouseUp={stopDrawing}
                                        onMouseLeave={stopDrawing}
                                        onTouchStart={startDrawing}
                                        onTouchMove={draw}
                                        onTouchEnd={stopDrawing}
                                    />
                                )}
                            </div>
                        </div>

                        {/* 드로잉 도구 바 */}
                        <div className="draw-toolbar">
                            {/* 펜 색상 선택 */}
                            <div className="tool-group">
                                {PEN_COLORS.map((pc) => (
                                    <button
                                        key={pc.id}
                                        className={`color-btn ${penColor === pc.color && !isEraser ? "active" : ""}`}
                                        style={{ "--btn-color": pc.color } as React.CSSProperties}
                                        onClick={() => { setPenColor(pc.color); setIsEraser(false); }}
                                        title={pc.label}
                                    >
                                        <span className="color-dot" />
                                    </button>
                                ))}
                            </div>

                            {/* 구분선 */}
                            <span className="tool-divider" />

                            {/* 굵기 조절 */}
                            <div className="tool-group">
                                <button
                                    className={`size-btn ${penSize === 1.5 && !isEraser ? "active" : ""}`}
                                    onClick={() => { setPenSize(1.5); setIsEraser(false); }}
                                    title="가늘게"
                                >
                                    <span className="size-dot size-thin" />
                                </button>
                                <button
                                    className={`size-btn ${penSize === 2.5 && !isEraser ? "active" : ""}`}
                                    onClick={() => { setPenSize(2.5); setIsEraser(false); }}
                                    title="보통"
                                >
                                    <span className="size-dot size-medium" />
                                </button>
                                <button
                                    className={`size-btn ${penSize === 5 && !isEraser ? "active" : ""}`}
                                    onClick={() => { setPenSize(5); setIsEraser(false); }}
                                    title="굵게"
                                >
                                    <span className="size-dot size-thick" />
                                </button>
                            </div>

                            {/* 구분선 */}
                            <span className="tool-divider" />

                            {/* 지우개 & 전체 지우기 */}
                            <div className="tool-group">
                                <button
                                    className={`tool-btn ${isEraser ? "active" : ""}`}
                                    onClick={() => setIsEraser(!isEraser)}
                                    title="지우개"
                                >
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="m7 21-4.3-4.3c-1-1-1-2.5 0-3.4l9.6-9.6c1-1 2.5-1 3.4 0l5.6 5.6c1 1 1 2.5 0 3.4L13 21" />
                                        <path d="M22 21H7" />
                                        <path d="m5 11 9 9" />
                                    </svg>
                                </button>
                                <button
                                    className="tool-btn"
                                    onClick={clearCanvas}
                                    title="전체 지우기"
                                >
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M3 6h18" />
                                        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                                        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                                    </svg>
                                </button>
                            </div>
                        </div>

                        {/* 네비게이션 */}
                        <div className="nav-buttons">
                            <button
                                className="nav-btn"
                                onClick={goPrev}
                                disabled={currentIndex <= 0}
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="15 18 9 12 15 6" />
                                </svg>
                                이전
                            </button>

                            <div className="progress-dots">
                                {images.map((_, idx) => (
                                    <span
                                        key={idx}
                                        className={`dot ${idx === currentIndex ? "active" : ""} ${idx < currentIndex ? "done" : ""}`}
                                    />
                                ))}
                            </div>

                            <button
                                className="nav-btn nav-btn-next"
                                onClick={goNext}
                            >
                                {currentIndex >= images.length - 1 ? "완료" : "다음"}
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="9 18 15 12 9 6" />
                                </svg>
                            </button>
                        </div>
                    </>
                )}

                {/* 완료 화면 */}
                {isFinished && !isReviewing && (() => {
                    const grading = getGradingResults();
                    return (
                        <div className="finish-screen">
                            <h2 className="finish-title">풀이 완료!</h2>
                            <p className="finish-total">총 소요 시간: <strong>{formatTime(totalElapsed)}</strong></p>

                            {/* 채점 결과 요약 */}
                            <div className="score-summary">
                                <div className="score-main">
                                    <span className="score-number">{grading.score}</span>
                                    <span className="score-unit">점</span>
                                </div>
                                <div className="score-details">
                                    <div className="score-item score-correct">
                                        <span className="score-icon">⭕</span>
                                        <span className="score-label">정답</span>
                                        <span className="score-count">{grading.correct}</span>
                                    </div>
                                    <div className="score-item score-wrong">
                                        <span className="score-icon">❌</span>
                                        <span className="score-label">오답</span>
                                        <span className="score-count">{grading.wrong}</span>
                                    </div>
                                    <div className="score-item score-unanswered">
                                        <span className="score-icon">➖</span>
                                        <span className="score-label">미응답</span>
                                        <span className="score-count">{grading.unanswered}</span>
                                    </div>
                                    {grading.unknown > 0 && (
                                        <div className="score-item score-unknown">
                                            <span className="score-icon">❓</span>
                                            <span className="score-label">미등록</span>
                                            <span className="score-count">{grading.unknown}</span>
                                        </div>
                                    )}
                                </div>
                                <p className="score-sub">
                                    채점 대상 {grading.gradable}문제 중 {grading.correct}문제 정답
                                </p>
                            </div>

                            <div className="finish-table-wrapper">
                                <table className="finish-table">
                                    <thead>
                                        <tr>
                                            <th>#</th>
                                            <th>과목</th>
                                            <th>문항</th>
                                            <th>선택</th>
                                            <th>정답</th>
                                            <th>결과</th>
                                            <th>소요 시간</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {images.map((img, idx) => {
                                            const result = getQuestionResult(idx);
                                            const hasKnownAnswer = getMappedQuestions(img).some(
                                                (q) => q.answer_key && q.answer_key !== "미정"
                                            );
                                            return (
                                                <tr
                                                    key={idx}
                                                    className={`result-row result-${result}`}
                                                    onClick={() => startReview(idx)}
                                                    style={{ cursor: "pointer" }}
                                                >
                                                    <td className="col-num">{idx + 1}</td>
                                                    <td className="col-subject">{img.subject}</td>
                                                    <td className="col-qno">{formatQuestionNos(img, idx + 1)}번</td>
                                                    <td className="col-answer">
                                                        <span className={`mapped-answer-text ${result === "correct" ? "mapped-answer-correct" : result === "wrong" ? "mapped-answer-wrong" : ""}`}>
                                                            {formatMappedSelectedAnswers(img, selectedAnswersByQuestionId)}
                                                        </span>
                                                    </td>
                                                    <td className="col-correct">
                                                        {hasKnownAnswer ? (
                                                            <span className="correct-badge">{formatMappedAnswerKey(img)}</span>
                                                        ) : (
                                                            <span className="answer-empty">미정</span>
                                                        )}
                                                    </td>
                                                    <td className="col-result">
                                                        {result === "correct" && <span className="result-mark mark-correct">⭕</span>}
                                                        {result === "wrong" && <span className="result-mark mark-wrong">❌</span>}
                                                        {result === "unanswered" && <span className="result-mark mark-unanswered">➖</span>}
                                                        {result === "unknown" && <span className="result-mark mark-unknown">❓</span>}
                                                    </td>
                                                    <td className="col-time">{formatTime(questionTimes[idx] || 0)}</td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>

                            {/* 풀이 기록 저장 상태 */}
                            <div className="save-status" style={{ textAlign: "center", margin: "12px 0 4px" }}>
                                {savingLogs && (
                                    <span style={{ color: "#a0a0a0", fontSize: "0.85rem" }}>풀이 기록 저장 중...</span>
                                )}
                                {logsSaved && (
                                    <span style={{ color: "#22c55e", fontSize: "0.85rem" }}>✅ 풀이 기록이 저장되었습니다</span>
                                )}
                                {!savingLogs && !logsSaved && isFinished && (
                                    <span style={{ color: "#ef4444", fontSize: "0.85rem" }}>⚠️ 풀이 기록 저장 실패 — <button onClick={() => saveSolvingLogs(questionTimes)} style={{ color: "#3b82f6", background: "none", border: "none", cursor: "pointer", textDecoration: "underline", fontSize: "0.85rem" }}>다시 시도</button></span>
                                )}
                            </div>

                            <p className="review-hint">문제를 클릭하면 다시 확인할 수 있습니다</p>

                            <div className="finish-actions">
                                <button className="action-btn" onClick={restart}>다시 풀기</button>
                                <button className="action-btn action-btn-review" onClick={() => startReview(0)}>전체 리뷰</button>
                                <a href="/test_exam" className="action-btn action-btn-outline">돌아가기</a>
                            </div>
                        </div>
                    );
                })()}

                {/* 리뷰 모드 */}
                {isFinished && isReviewing && reviewImage && (
                    <>
                        {/* 리뷰 상단 바 */}
                        <div className="review-bar">
                            <button className="review-back-btn" onClick={exitReview}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="15 18 9 12 15 6" />
                                </svg>
                                결과로 돌아가기
                            </button>
                            <div className="review-info-badge">
                                {reviewResult === "correct" && <span className="review-result-tag tag-correct">⭕ 정답</span>}
                                {reviewResult === "wrong" && <span className="review-result-tag tag-wrong">❌ 오답</span>}
                                {reviewResult === "unanswered" && <span className="review-result-tag tag-unanswered">➖ 미응답</span>}
                                {reviewResult === "unknown" && <span className="review-result-tag tag-unknown">❓ 미등록</span>}
                            </div>
                        </div>

                        {/* 문제 정보 바 */}
                        <div className="question-info">
                            <span className="q-number">{reviewIndex + 1} / {images.length}</span>
                            <span className="q-meta">
                                {reviewImage.year}년 {reviewImage.exam_type} {reviewImage.subject} {formatQuestionNos(reviewImage, reviewIndex + 1)}번
                            </span>
                        </div>

                        {/* 문제 이미지 + 정답/선택 표시 */}
                        <div className="question-area">
                            {/* 왼쪽 정답 확인 패널 */}
                            <div className="answer-panel review-answer-panel">
                                <span className="answer-label">내 선택</span>
                                {[1, 2, 3, 4].map((num) => {
                                    const myAnswer = activeReviewMappedQuestion ? getSelectedAnswer(activeReviewMappedQuestion.question_id) : null;
                                    const correctAnswer = activeReviewMappedQuestion?.answer_key && activeReviewMappedQuestion.answer_key !== "미정"
                                        ? parseInt(activeReviewMappedQuestion.answer_key) : null;
                                    const isSelected = myAnswer === num;
                                    const isCorrect = correctAnswer === num;

                                    let btnClass = "answer-btn review-btn";
                                    if (isSelected && isCorrect) btnClass += " review-correct";
                                    else if (isSelected && !isCorrect) btnClass += " review-wrong";
                                    else if (isCorrect) btnClass += " review-correct-hint";

                                    return (
                                        <button key={num} className={btnClass} disabled>
                                            {num}
                                        </button>
                                    );
                                })}
                                {reviewMappedQuestions.length > 1 && (
                                    <div className="mapped-qnos">
                                        {reviewMappedQuestions.map((q) => (
                                            <button
                                                key={q.question_id}
                                                className={`mapped-qno-chip ${activeReviewMappedQuestion?.question_id === q.question_id ? "active" : ""}`}
                                                onClick={() => {
                                                    stopAudio();
                                                    setShowCommentary(false);
                                                    setActiveMappedQuestionNoByIndex((prev) => ({ ...prev, [reviewIndex]: q.question_no }));
                                                }}
                                            >
                                                {q.question_no}번
                                            </button>
                                        ))}
                                    </div>
                                )}
                                {activeReviewMappedQuestion?.answer_key && activeReviewMappedQuestion.answer_key !== "미정" && (
                                    <span className="review-correct-label">
                                        정답: {activeReviewMappedQuestion.answer_key}
                                        {reviewMappedQuestions.length > 1 ? ` (${activeReviewMappedQuestion.question_no}번)` : ""}
                                    </span>
                                )}

                                {/* 해설 버튼 */}
                                <button
                                    className={`commentary-toggle-btn ${showCommentary ? "active" : ""}`}
                                    onClick={() => activeReviewMappedQuestion && fetchCommentary(activeReviewMappedQuestion.question_id)}
                                    disabled={commentaryLoading || !activeReviewMappedQuestion}
                                >
                                    {commentaryLoading ? (
                                        <div className="spinner-sm" />
                                    ) : (
                                        <>
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                                                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                                            </svg>
                                            해설
                                        </>
                                    )}
                                </button>

                                {/* TTS 음성 해설 (오답 문제) */}
                                {reviewResult === "wrong" && (
                                    <div className="tts-btn-group">
                                        <button
                                            className={`tts-play-btn ${playingQuestionId === activeReviewMappedQuestion?.question_id ? "playing" : ""} ${activeReviewMappedQuestion && audioNoteMap[activeReviewMappedQuestion.question_id] ? "generated" : ""}`}
                                            onClick={() => activeReviewMappedQuestion && handleTTSPlay(activeReviewMappedQuestion.question_id)}
                                            disabled={!activeReviewMappedQuestion || generatingTTS === activeReviewMappedQuestion.question_id}
                                        >
                                            {activeReviewMappedQuestion && generatingTTS === activeReviewMappedQuestion.question_id ? (
                                                <><div className="spinner-sm" /><span>생성 중</span></>
                                            ) : activeReviewMappedQuestion && playingQuestionId === activeReviewMappedQuestion.question_id ? (
                                                <>
                                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                                                        <rect x="6" y="4" width="4" height="16" rx="1" />
                                                        <rect x="14" y="4" width="4" height="16" rx="1" />
                                                    </svg>
                                                    <span>일시정지</span>
                                                </>
                                            ) : activeReviewMappedQuestion && audioNoteMap[activeReviewMappedQuestion.question_id] ? (
                                                <>
                                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                                                        <polygon points="5 3 19 12 5 21 5 3" />
                                                    </svg>
                                                    <span>다시 듣기</span>
                                                </>
                                            ) : (
                                                <>
                                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                                        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                                                        <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                                                    </svg>
                                                    <span>음성 해설</span>
                                                </>
                                            )}
                                        </button>
                                        {activeReviewMappedQuestion && playingQuestionId === activeReviewMappedQuestion.question_id && (
                                            <button className="tts-stop-btn" onClick={stopAudio} title="정지">
                                                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                                                    <rect x="4" y="4" width="16" height="16" rx="2" />
                                                </svg>
                                            </button>
                                        )}
                                        {activeReviewMappedQuestion && audioNoteMap[activeReviewMappedQuestion.question_id] && playingQuestionId !== activeReviewMappedQuestion.question_id && (
                                            <span className="tts-saved-badge">저장됨</span>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* 이미지 */}
                            <div ref={containerRef} className="image-wrapper">
                                {!imageLoaded && (
                                    <div className="image-loading">
                                        <div className="spinner" />
                                    </div>
                                )}
                                <img
                                    ref={imgRef}
                                    key={reviewImage.image_id}
                                    src={`${backendUrl}/api/v1/admin/questions/images/serve/${reviewImage.image_id}`}
                                    alt={`문제 ${reviewImage.question_no}`}
                                    className={`question-image ${imageLoaded ? "loaded" : ""}`}
                                    onLoad={handleImageLoad}
                                    onError={() => setImageLoaded(true)}
                                    draggable={false}
                                />
                            </div>
                        </div>

                        {/* 해설 펼침 영역 */}
                        {showCommentary && (
                            <div className="commentary-section">
                                <div className="commentary-header">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                                        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                                    </svg>
                                    <span>해설</span>
                                    <button className="commentary-close" onClick={() => setShowCommentary(false)}>
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <line x1="18" y1="6" x2="6" y2="18" />
                                            <line x1="6" y1="6" x2="18" y2="18" />
                                        </svg>
                                    </button>
                                </div>
                                <div className="commentary-body">
                                    {commentaryMap[reviewImage.question_id] != null ? (
                                        <div className="commentary-text">
                                            {commentaryMap[reviewImage.question_id]!.split("\n").map((line, i) => (
                                                <p key={i}>{line || "\u00A0"}</p>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="commentary-empty">등록된 해설이 없습니다.</p>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* 리뷰 네비게이션 */}
                        <div className="nav-buttons">
                            <button className="nav-btn" onClick={reviewPrev} disabled={reviewIndex <= 0}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="15 18 9 12 15 6" />
                                </svg>
                                이전
                            </button>

                            <div className="progress-dots">
                                {images.map((_, idx) => {
                                    const r = getQuestionResult(idx);
                                    return (
                                        <span
                                            key={idx}
                                            className={`dot ${idx === reviewIndex ? "active" : ""} ${r === "correct" ? "dot-correct" : r === "wrong" ? "dot-wrong" : r === "unanswered" ? "dot-unanswered" : ""}`}
                                            onClick={() => {
                                                stopAudio();
                                                setImageLoaded(false);
                                                setShowCommentary(false);
                                                setReviewIndex(idx);
                                                const firstMappedQno = getMappedQuestions(images[idx])[0]?.question_no;
                                                if (firstMappedQno != null) {
                                                    setActiveMappedQuestionNoByIndex((prev) => ({ ...prev, [idx]: firstMappedQno }));
                                                }
                                            }}
                                            style={{ cursor: "pointer" }}
                                        />
                                    );
                                })}
                            </div>

                            <button className="nav-btn" onClick={reviewNext} disabled={reviewIndex >= images.length - 1}>
                                다음
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="9 18 15 12 9 6" />
                                </svg>
                            </button>
                        </div>
                    </>
                )}
            </div>

            {/* 숨겨진 오디오 플레이어 */}
            <audio
                ref={audioRef}
                onEnded={() => setPlayingQuestionId(null)}
                onError={() => { console.error("[TTS] 오디오 재생 오류"); setPlayingQuestionId(null); }}
                style={{ display: "none" }}
            />

            {/* 하단 네비게이션 */}
            <div className="bottom-nav">
                <a href="/test_exam" className="nav-link">모의고사</a>
                <span className="nav-divider">·</span>
                <a href="/chat" className="nav-link">채팅으로</a>
                <span className="nav-divider">·</span>
                <a href="/" className="nav-link">홈으로</a>
            </div>

            <style jsx>{`
                /* ── 컨테이너 ── */
                .exam-container {
                    position: relative;
                    width: 100vw;
                    min-height: 100vh;
                    background: #000;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    overflow-x: hidden;
                    font-family: "Gothic A1", "Noto Sans KR", "Malgun Gothic", "맑은 고딕", sans-serif;
                }

                /* ── 파티클 ── */
                .particles { position: fixed; inset: 0; pointer-events: none; z-index: 0; }
                .particle {
                    position: absolute; bottom: -20px; width: 2px; height: 2px;
                    background: rgba(255,255,255,0.6); border-radius: 50%;
                    animation: rise linear infinite;
                }
                @keyframes rise {
                    0%   { transform: translateY(0) scale(1); opacity: 0; }
                    10%  { opacity: 0.4; }
                    90%  { opacity: 0.1; }
                    100% { transform: translateY(-100vh) scale(0.3); opacity: 0; }
                }

                /* ── 상단 로고 ── */
                .top-logo {
                    position: fixed; top: 28px; left: 32px; display: flex; gap: 2px;
                    text-decoration: none; font-size: 1.2rem; font-weight: 900;
                    color: #fff; letter-spacing: 0.05em; z-index: 100;
                }

                /* ── 타이머 ── */
                .timer-area {
                    position: fixed; top: 24px; right: 32px; z-index: 100;
                    display: flex; flex-direction: column; align-items: flex-end; gap: 6px;
                }
                .timer-total, .timer-question {
                    display: flex; align-items: center; gap: 10px;
                    padding: 8px 16px; border-radius: 10px;
                    background: rgba(255,255,255,0.03);
                    border: 1px solid rgba(255,255,255,0.06);
                    backdrop-filter: blur(12px);
                }
                .timer-label {
                    font-size: 0.7rem; color: rgba(255,255,255,0.3);
                    letter-spacing: 0.05em; min-width: 52px;
                }
                .timer-value {
                    font-size: 1.05rem; font-weight: 600; color: rgba(255,255,255,0.7);
                    font-variant-numeric: tabular-nums; letter-spacing: 0.06em;
                    min-width: 60px; text-align: right;
                }
                .timer-value-accent { color: rgba(255,255,255,0.95); }

                /* ── 콘텐츠 ── */
                .content {
                    position: relative; z-index: 1;
                    display: flex; flex-direction: column; align-items: center;
                    width: 100%; max-width: 800px;
                    padding: 100px 24px 80px;
                    animation: fadeIn 0.6s ease-out;
                    flex: 1;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(16px); }
                    to   { opacity: 1; transform: translateY(0); }
                }

                /* ── 로딩 / 에러 ── */
                .state-message {
                    display: flex; flex-direction: column; align-items: center;
                    gap: 16px; margin-top: 80px;
                }
                .state-message p {
                    font-size: 0.9rem; color: rgba(255,255,255,0.4);
                    letter-spacing: 0.03em;
                }
                .error-text { color: rgba(239,68,68,0.7) !important; }
                .spinner {
                    width: 24px; height: 24px;
                    border: 2px solid rgba(255,255,255,0.08);
                    border-top-color: rgba(255,255,255,0.5);
                    border-radius: 50%; animation: spin 0.8s linear infinite;
                }
                @keyframes spin { to { transform: rotate(360deg); } }

                /* ── 문제 정보 바 ── */
                .question-info {
                    display: flex; align-items: center; gap: 16px;
                    margin-bottom: 20px; width: 100%;
                }
                .q-number {
                    font-size: 0.85rem; font-weight: 600; color: rgba(255,255,255,0.8);
                    padding: 4px 12px; border-radius: 8px;
                    background: rgba(255,255,255,0.06);
                    letter-spacing: 0.05em;
                }
                .q-meta {
                    font-size: 0.78rem; color: rgba(255,255,255,0.35);
                    letter-spacing: 0.03em;
                }

                /* ── 문제 영역 (정답 버튼 + 이미지) ── */
                .question-area {
                    display: flex; align-items: stretch; gap: 12px;
                    width: 100%; margin-bottom: 16px;
                }

                /* ── 정답 선택 패널 ── */
                .answer-panel {
                    display: flex; flex-direction: column; align-items: center;
                    gap: 8px; padding: 12px 6px;
                    border-radius: 14px;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                    backdrop-filter: blur(12px);
                    flex-shrink: 0;
                }
                .answer-label {
                    font-size: 0.6rem; font-weight: 600;
                    color: rgba(255,255,255,0.25);
                    letter-spacing: 0.1em;
                    margin-bottom: 2px;
                }
                .answer-sub-label {
                    font-size: 0.55rem;
                    color: rgba(255,255,255,0.35);
                    letter-spacing: 0.06em;
                    margin-bottom: 2px;
                }
                .answer-group {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 6px;
                    margin-bottom: 6px;
                }
                .answer-group:last-child { margin-bottom: 0; }
                .answer-btn {
                    width: 40px; height: 40px;
                    border-radius: 50%;
                    border: 1.5px solid rgba(255,255,255,0.12);
                    background: rgba(255,255,255,0.03);
                    color: rgba(255,255,255,0.45);
                    font-size: 0.9rem; font-weight: 700;
                    font-family: inherit; cursor: pointer;
                    display: flex; align-items: center; justify-content: center;
                    transition: all 0.25s ease;
                    padding: 0;
                }
                .answer-btn:hover {
                    background: rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.8);
                    border-color: rgba(255,255,255,0.25);
                    transform: scale(1.08);
                }
                .answer-btn.selected {
                    background: rgba(59,130,246,0.2);
                    border-color: rgba(59,130,246,0.6);
                    color: #fff;
                    box-shadow: 0 0 16px rgba(59,130,246,0.25), inset 0 0 8px rgba(59,130,246,0.1);
                    transform: scale(1.08);
                }

                /* ── 이미지 + 캔버스 래퍼 ── */
                .image-wrapper {
                    position: relative; width: 100%; flex: 1; min-width: 0;
                    min-height: 300px;
                    border-radius: 16px; overflow: hidden;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                    display: flex; align-items: center; justify-content: center;
                    touch-action: none; /* 터치 드로잉 시 스크롤 방지 */
                }
                .image-loading {
                    position: absolute; inset: 0;
                    display: flex; align-items: center; justify-content: center;
                    background: rgba(0,0,0,0.5);
                    z-index: 5;
                }
                .question-image {
                    width: 100%; height: auto; display: block;
                    opacity: 0; transition: opacity 0.4s ease;
                    background: #fff;
                    border-radius: 12px;
                    pointer-events: none; /* 이미지 드래그 방지, 터치/클릭은 캔버스로 */
                    user-select: none;
                    -webkit-user-drag: none;
                }
                .question-image.loaded { opacity: 1; }

                /* ── OHP 캔버스 오버레이 ── */
                .draw-canvas {
                    position: absolute;
                    top: 0; left: 0;
                    cursor: crosshair;
                    z-index: 3;
                    border-radius: 12px;
                }

                /* ── 드로잉 도구 바 ── */
                .draw-toolbar {
                    display: flex; align-items: center; gap: 8px;
                    padding: 8px 16px; border-radius: 12px;
                    background: rgba(255,255,255,0.03);
                    border: 1px solid rgba(255,255,255,0.06);
                    backdrop-filter: blur(12px);
                    margin-bottom: 20px;
                    flex-wrap: wrap; justify-content: center;
                }

                .tool-group {
                    display: flex; align-items: center; gap: 4px;
                }

                .tool-divider {
                    width: 1px; height: 20px;
                    background: rgba(255,255,255,0.08);
                    margin: 0 4px;
                }

                /* ── 색상 버튼 ── */
                .color-btn {
                    width: 28px; height: 28px;
                    border-radius: 50%; border: 2px solid transparent;
                    background: transparent; cursor: pointer;
                    display: flex; align-items: center; justify-content: center;
                    transition: all 0.2s ease;
                    padding: 0;
                }
                .color-btn .color-dot {
                    width: 14px; height: 14px; border-radius: 50%;
                    background: var(--btn-color);
                    transition: all 0.2s ease;
                }
                .color-btn:hover .color-dot {
                    transform: scale(1.15);
                    box-shadow: 0 0 8px var(--btn-color);
                }
                .color-btn.active {
                    border-color: rgba(255,255,255,0.4);
                }
                .color-btn.active .color-dot {
                    box-shadow: 0 0 10px var(--btn-color);
                    transform: scale(1.1);
                }

                /* ── 굵기 버튼 ── */
                .size-btn {
                    width: 28px; height: 28px;
                    border-radius: 8px; border: 1px solid transparent;
                    background: transparent; cursor: pointer;
                    display: flex; align-items: center; justify-content: center;
                    transition: all 0.2s ease;
                    padding: 0;
                }
                .size-btn:hover { background: rgba(255,255,255,0.06); }
                .size-btn.active {
                    border-color: rgba(255,255,255,0.2);
                    background: rgba(255,255,255,0.06);
                }
                .size-dot {
                    border-radius: 50%; background: rgba(255,255,255,0.6);
                }
                .size-thin  { width: 4px;  height: 4px;  }
                .size-medium { width: 7px;  height: 7px;  }
                .size-thick  { width: 11px; height: 11px; }

                /* ── 도구 버튼 (지우개 / 전체 지우기) ── */
                .tool-btn {
                    width: 32px; height: 32px;
                    border-radius: 8px; border: 1px solid transparent;
                    background: transparent; cursor: pointer;
                    display: flex; align-items: center; justify-content: center;
                    color: rgba(255,255,255,0.4);
                    transition: all 0.2s ease;
                    padding: 0;
                }
                .tool-btn:hover {
                    background: rgba(255,255,255,0.06);
                    color: rgba(255,255,255,0.8);
                }
                .tool-btn.active {
                    border-color: rgba(255,255,255,0.2);
                    background: rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.9);
                }

                /* ── 네비게이션 버튼 ── */
                .nav-buttons {
                    display: flex; align-items: center; gap: 20px;
                    width: 100%; justify-content: space-between;
                }
                .nav-btn {
                    display: flex; align-items: center; gap: 6px;
                    padding: 10px 20px; border-radius: 10px;
                    background: rgba(255,255,255,0.03);
                    border: 1px solid rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.5); font-size: 0.82rem;
                    font-family: inherit; cursor: pointer;
                    letter-spacing: 0.05em; transition: all 0.25s ease;
                }
                .nav-btn:hover:not(:disabled) {
                    background: rgba(255,255,255,0.07);
                    color: rgba(255,255,255,0.9);
                    border-color: rgba(255,255,255,0.15);
                }
                .nav-btn:disabled {
                    opacity: 0.25; cursor: not-allowed;
                }
                .nav-btn-next {
                    background: rgba(255,255,255,0.06);
                    color: rgba(255,255,255,0.7);
                }
                .nav-btn-next:hover:not(:disabled) {
                    background: rgba(255,255,255,0.12);
                    color: #fff;
                }

                /* ── 진행 도트 ── */
                .progress-dots {
                    display: flex; gap: 5px; flex-wrap: wrap;
                    justify-content: center; max-width: 300px;
                }
                .dot {
                    width: 6px; height: 6px; border-radius: 50%;
                    background: rgba(255,255,255,0.1);
                    transition: all 0.3s ease;
                }
                .dot.active {
                    background: rgba(255,255,255,0.9);
                    box-shadow: 0 0 8px rgba(255,255,255,0.4);
                    transform: scale(1.3);
                }
                .dot.done { background: rgba(255,255,255,0.35); }

                /* ── 완료 화면 ── */
                .finish-screen {
                    display: flex; flex-direction: column; align-items: center;
                    width: 100%; animation: fadeIn 0.6s ease-out;
                }
                .finish-title {
                    font-size: 1.6rem; font-weight: 700; color: rgba(255,255,255,0.9);
                    letter-spacing: 0.1em; margin: 0 0 12px 0;
                    text-shadow: 0 0 30px rgba(255,255,255,0.08);
                }
                .finish-total {
                    font-size: 0.9rem; color: rgba(255,255,255,0.4);
                    margin: 0 0 32px 0; letter-spacing: 0.03em;
                }
                .finish-total strong {
                    color: rgba(255,255,255,0.8); font-weight: 600;
                }

                .finish-table-wrapper {
                    width: 100%; max-height: 400px; overflow-y: auto;
                    border-radius: 12px;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                    margin-bottom: 28px;
                }
                .finish-table-wrapper::-webkit-scrollbar { width: 4px; }
                .finish-table-wrapper::-webkit-scrollbar-track { background: transparent; }
                .finish-table-wrapper::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

                .finish-table {
                    width: 100%; border-collapse: collapse;
                }
                .finish-table th {
                    padding: 12px 16px; font-size: 0.72rem; font-weight: 600;
                    color: rgba(255,255,255,0.4); letter-spacing: 0.08em;
                    text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06);
                    position: sticky; top: 0; background: rgba(10,10,10,0.95);
                    backdrop-filter: blur(8px);
                }
                .finish-table td {
                    padding: 10px 16px; font-size: 0.8rem;
                    color: rgba(255,255,255,0.5);
                    border-bottom: 1px solid rgba(255,255,255,0.03);
                }
                .col-num { color: rgba(255,255,255,0.25); font-weight: 500; width: 40px; }
                .col-subject { color: rgba(255,255,255,0.6); }
                .col-qno { color: rgba(255,255,255,0.4); }
                .col-answer { text-align: center; }
                .answer-badge {
                    display: inline-flex; align-items: center; justify-content: center;
                    width: 24px; height: 24px; border-radius: 50%;
                    background: rgba(59,130,246,0.15);
                    border: 1px solid rgba(59,130,246,0.3);
                    color: rgba(59,130,246,0.9);
                    font-size: 0.72rem; font-weight: 700;
                }
                .answer-empty { color: rgba(255,255,255,0.15); }
                .mapped-answer-text {
                    font-size: 0.72rem;
                    color: rgba(255,255,255,0.5);
                }
                .mapped-answer-correct { color: rgba(34,197,94,0.85); }
                .mapped-answer-wrong { color: rgba(239,68,68,0.85); }

                /* ── 채점 결과 배지 변형 ── */
                .badge-correct {
                    background: rgba(34,197,94,0.15);
                    border-color: rgba(34,197,94,0.4);
                    color: rgba(34,197,94,0.9);
                }
                .badge-wrong {
                    background: rgba(239,68,68,0.15);
                    border-color: rgba(239,68,68,0.4);
                    color: rgba(239,68,68,0.9);
                }

                /* ── 정답 표시 컬럼 ── */
                .col-correct { text-align: center; }
                .correct-badge {
                    display: inline-flex; align-items: center; justify-content: center;
                    width: 24px; height: 24px; border-radius: 50%;
                    background: rgba(34,197,94,0.1);
                    border: 1px solid rgba(34,197,94,0.25);
                    color: rgba(34,197,94,0.8);
                    font-size: 0.72rem; font-weight: 700;
                }
                .col-result { text-align: center; width: 50px; }
                .result-mark { font-size: 0.85rem; }
                .mark-correct { filter: brightness(1.2); }
                .mark-wrong { filter: brightness(1.2); }
                .mark-unanswered { opacity: 0.4; }
                .mark-unknown { opacity: 0.4; }

                /* ── 행 결과별 배경색 ── */
                .result-row { transition: background 0.2s ease; }
                .result-row:hover { background: rgba(255,255,255,0.03); }
                .result-row.result-correct { border-left: 2px solid rgba(34,197,94,0.3); }
                .result-row.result-wrong { border-left: 2px solid rgba(239,68,68,0.3); }

                .col-time {
                    font-variant-numeric: tabular-nums; font-weight: 600;
                    color: rgba(255,255,255,0.7); letter-spacing: 0.05em;
                }

                /* ── 점수 요약 ── */
                .score-summary {
                    display: flex; flex-direction: column; align-items: center;
                    gap: 16px; margin-bottom: 28px;
                    padding: 28px 40px; border-radius: 16px;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                    backdrop-filter: blur(12px);
                    width: 100%; max-width: 420px;
                }
                .score-main {
                    display: flex; align-items: baseline; gap: 4px;
                }
                .score-number {
                    font-size: 3.2rem; font-weight: 800;
                    color: rgba(255,255,255,0.95);
                    letter-spacing: -0.02em;
                    line-height: 1;
                    text-shadow: 0 0 40px rgba(255,255,255,0.1);
                }
                .score-unit {
                    font-size: 1.1rem; font-weight: 500;
                    color: rgba(255,255,255,0.35);
                }
                .score-details {
                    display: flex; gap: 20px; flex-wrap: wrap;
                    justify-content: center;
                }
                .score-item {
                    display: flex; align-items: center; gap: 6px;
                    padding: 6px 14px; border-radius: 8px;
                    background: rgba(255,255,255,0.03);
                    border: 1px solid rgba(255,255,255,0.05);
                }
                .score-icon { font-size: 0.82rem; }
                .score-label {
                    font-size: 0.72rem; color: rgba(255,255,255,0.4);
                    letter-spacing: 0.05em;
                }
                .score-count {
                    font-size: 0.9rem; font-weight: 700;
                    color: rgba(255,255,255,0.8);
                    min-width: 18px; text-align: center;
                }
                .score-correct .score-count { color: rgba(34,197,94,0.9); }
                .score-wrong .score-count { color: rgba(239,68,68,0.9); }
                .score-unanswered .score-count { color: rgba(255,255,255,0.35); }
                .score-unknown .score-count { color: rgba(250,204,21,0.8); }
                .score-sub {
                    font-size: 0.72rem; color: rgba(255,255,255,0.25);
                    letter-spacing: 0.03em; margin: 0;
                }

                .review-hint {
                    font-size: 0.7rem; color: rgba(255,255,255,0.2);
                    letter-spacing: 0.03em; margin: 0 0 16px 0;
                }

                .finish-actions {
                    display: flex; gap: 16px;
                }
                .action-btn-review {
                    background: rgba(59,130,246,0.1);
                    border-color: rgba(59,130,246,0.2);
                    color: rgba(59,130,246,0.8);
                }
                .action-btn-review:hover {
                    background: rgba(59,130,246,0.2);
                    border-color: rgba(59,130,246,0.4);
                    color: rgba(59,130,246,1);
                }

                /* ── 리뷰 모드 ── */
                .review-bar {
                    display: flex; align-items: center; justify-content: space-between;
                    width: 100%; margin-bottom: 16px;
                    padding: 10px 16px; border-radius: 12px;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.06);
                    backdrop-filter: blur(12px);
                }
                .review-back-btn {
                    display: flex; align-items: center; gap: 6px;
                    padding: 6px 14px; border-radius: 8px;
                    background: rgba(255,255,255,0.04);
                    border: 1px solid rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.5); font-size: 0.78rem;
                    font-family: inherit; cursor: pointer;
                    letter-spacing: 0.04em; transition: all 0.2s ease;
                }
                .review-back-btn:hover {
                    background: rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.9);
                }
                .review-info-badge { display: flex; gap: 8px; }
                .review-result-tag {
                    padding: 5px 14px; border-radius: 20px;
                    font-size: 0.75rem; font-weight: 600;
                    letter-spacing: 0.05em;
                }
                .tag-correct {
                    background: rgba(34,197,94,0.1); color: rgba(34,197,94,0.9);
                    border: 1px solid rgba(34,197,94,0.25);
                }
                .tag-wrong {
                    background: rgba(239,68,68,0.1); color: rgba(239,68,68,0.9);
                    border: 1px solid rgba(239,68,68,0.25);
                }
                .tag-unanswered {
                    background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.4);
                    border: 1px solid rgba(255,255,255,0.08);
                }
                .tag-unknown {
                    background: rgba(250,204,21,0.08); color: rgba(250,204,21,0.7);
                    border: 1px solid rgba(250,204,21,0.2);
                }

                /* ── 리뷰 모드 정답 버튼 ── */
                .review-answer-panel { pointer-events: auto; }
                .review-btn {
                    cursor: default !important;
                    opacity: 0.5;
                }
                .review-btn.review-correct {
                    background: rgba(34,197,94,0.25) !important;
                    border-color: rgba(34,197,94,0.6) !important;
                    color: #fff !important;
                    box-shadow: 0 0 16px rgba(34,197,94,0.3), inset 0 0 8px rgba(34,197,94,0.15) !important;
                    opacity: 1;
                    transform: scale(1.08);
                }
                .review-btn.review-wrong {
                    background: rgba(239,68,68,0.25) !important;
                    border-color: rgba(239,68,68,0.6) !important;
                    color: #fff !important;
                    box-shadow: 0 0 16px rgba(239,68,68,0.3), inset 0 0 8px rgba(239,68,68,0.15) !important;
                    opacity: 1;
                    transform: scale(1.08);
                }
                .review-btn.review-correct-hint {
                    background: rgba(34,197,94,0.1) !important;
                    border-color: rgba(34,197,94,0.35) !important;
                    border-style: dashed !important;
                    color: rgba(34,197,94,0.8) !important;
                    opacity: 1;
                }
                .review-correct-label {
                    font-size: 0.6rem; font-weight: 600;
                    color: rgba(34,197,94,0.6);
                    letter-spacing: 0.06em;
                    margin-top: 4px;
                    text-align: center;
                }
                .mapped-qnos {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 4px;
                    margin-top: 6px;
                    width: 100%;
                    justify-content: center;
                }
                .mapped-qno-chip {
                    border: 1px solid rgba(255,255,255,0.14);
                    background: rgba(255,255,255,0.04);
                    color: rgba(255,255,255,0.56);
                    font-size: 0.58rem;
                    border-radius: 7px;
                    padding: 4px 7px;
                    cursor: pointer;
                    font-family: inherit;
                    transition: all 0.2s ease;
                }
                .mapped-qno-chip:hover {
                    border-color: rgba(250,204,21,0.4);
                    color: rgba(250,204,21,0.9);
                }
                .mapped-qno-chip.active {
                    border-color: rgba(250,204,21,0.45);
                    background: rgba(250,204,21,0.12);
                    color: rgba(250,204,21,0.95);
                }

                /* ── 해설 토글 버튼 ── */
                .commentary-toggle-btn {
                    display: flex; align-items: center; justify-content: center;
                    gap: 4px; margin-top: 8px;
                    padding: 8px 10px; border-radius: 8px;
                    background: rgba(250,204,21,0.08);
                    border: 1px solid rgba(250,204,21,0.2);
                    color: rgba(250,204,21,0.7);
                    font-size: 0.65rem; font-weight: 600;
                    font-family: inherit; cursor: pointer;
                    letter-spacing: 0.06em;
                    transition: all 0.25s ease;
                    width: 100%;
                }
                .commentary-toggle-btn:hover:not(:disabled) {
                    background: rgba(250,204,21,0.15);
                    border-color: rgba(250,204,21,0.4);
                    color: rgba(250,204,21,0.95);
                }
                .commentary-toggle-btn.active {
                    background: rgba(250,204,21,0.15);
                    border-color: rgba(250,204,21,0.4);
                    color: rgba(250,204,21,0.95);
                    box-shadow: 0 0 12px rgba(250,204,21,0.15);
                }
                .commentary-toggle-btn:disabled {
                    opacity: 0.5; cursor: wait;
                }
                .spinner-sm {
                    width: 14px; height: 14px;
                    border: 1.5px solid rgba(250,204,21,0.15);
                    border-top-color: rgba(250,204,21,0.6);
                    border-radius: 50%; animation: spin 0.7s linear infinite;
                }

                /* ── 해설 펼침 영역 ── */
                .commentary-section {
                    width: 100%; margin-bottom: 16px;
                    border-radius: 14px;
                    background: rgba(250,204,21,0.03);
                    border: 1px solid rgba(250,204,21,0.12);
                    backdrop-filter: blur(12px);
                    overflow: hidden;
                    animation: slideDown 0.35s ease-out;
                }
                @keyframes slideDown {
                    from { opacity: 0; max-height: 0; transform: translateY(-8px); }
                    to   { opacity: 1; max-height: 2000px; transform: translateY(0); }
                }
                .commentary-header {
                    display: flex; align-items: center; gap: 8px;
                    padding: 12px 16px;
                    border-bottom: 1px solid rgba(250,204,21,0.08);
                    color: rgba(250,204,21,0.7);
                    font-size: 0.8rem; font-weight: 600;
                    letter-spacing: 0.05em;
                }
                .commentary-close {
                    margin-left: auto;
                    background: none; border: none; cursor: pointer;
                    color: rgba(255,255,255,0.3); padding: 4px;
                    border-radius: 4px;
                    transition: all 0.2s ease;
                    display: flex; align-items: center; justify-content: center;
                }
                .commentary-close:hover {
                    color: rgba(255,255,255,0.7);
                    background: rgba(255,255,255,0.06);
                }
                .commentary-body {
                    padding: 16px 20px;
                    max-height: 400px; overflow-y: auto;
                }
                .commentary-body::-webkit-scrollbar { width: 4px; }
                .commentary-body::-webkit-scrollbar-track { background: transparent; }
                .commentary-body::-webkit-scrollbar-thumb { background: rgba(250,204,21,0.15); border-radius: 2px; }
                .commentary-text p {
                    margin: 0 0 6px 0;
                    font-size: 0.82rem; line-height: 1.7;
                    color: rgba(255,255,255,0.65);
                    letter-spacing: 0.02em;
                }
                .commentary-empty {
                    font-size: 0.8rem; color: rgba(255,255,255,0.25);
                    text-align: center; padding: 20px 0;
                    letter-spacing: 0.03em; margin: 0;
                }

                /* ── 리뷰 도트 결과별 색상 ── */
                .dot-correct { background: rgba(34,197,94,0.6); }
                .dot-wrong { background: rgba(239,68,68,0.6); }
                .dot-unanswered { background: rgba(255,255,255,0.15); }

                /* ── TTS 음성 해설 ── */
                .tts-btn-group {
                    display: flex; align-items: center; gap: 4px;
                    margin-top: 4px; width: 100%;
                }
                .tts-play-btn {
                    display: flex; align-items: center; justify-content: center;
                    gap: 4px; flex: 1;
                    padding: 8px 8px; border-radius: 8px;
                    background: rgba(99,102,241,0.08);
                    border: 1px solid rgba(99,102,241,0.2);
                    color: rgba(99,102,241,0.7);
                    font-size: 0.62rem; font-weight: 600;
                    font-family: inherit; cursor: pointer;
                    letter-spacing: 0.05em;
                    transition: all 0.25s ease;
                }
                .tts-play-btn:hover:not(:disabled) {
                    background: rgba(99,102,241,0.15);
                    border-color: rgba(99,102,241,0.4);
                    color: rgba(99,102,241,0.95);
                }
                .tts-play-btn:disabled {
                    opacity: 0.6; cursor: wait;
                }
                .tts-play-btn.playing {
                    background: rgba(99,102,241,0.15);
                    border-color: rgba(99,102,241,0.4);
                    color: rgba(99,102,241,0.95);
                    box-shadow: 0 0 12px rgba(99,102,241,0.15);
                    animation: pulse-glow 2s ease-in-out infinite;
                }
                .tts-play-btn.generated {
                    border-color: rgba(34,197,94,0.25);
                }
                @keyframes pulse-glow {
                    0%, 100% { box-shadow: 0 0 8px rgba(99,102,241,0.1); }
                    50% { box-shadow: 0 0 16px rgba(99,102,241,0.25); }
                }
                .tts-play-btn span {
                    white-space: nowrap;
                }
                .tts-stop-btn {
                    width: 28px; height: 28px;
                    border-radius: 6px; border: 1px solid rgba(239,68,68,0.2);
                    background: rgba(239,68,68,0.08);
                    color: rgba(239,68,68,0.6);
                    cursor: pointer; display: flex;
                    align-items: center; justify-content: center;
                    transition: all 0.2s ease;
                    flex-shrink: 0; padding: 0;
                }
                .tts-stop-btn:hover {
                    background: rgba(239,68,68,0.15);
                    border-color: rgba(239,68,68,0.4);
                    color: rgba(239,68,68,0.9);
                }
                .tts-saved-badge {
                    font-size: 0.55rem; color: rgba(34,197,94,0.6);
                    letter-spacing: 0.04em; white-space: nowrap;
                    flex-shrink: 0;
                }

                /* ── 액션 버튼 ── */
                .action-btn {
                    display: inline-flex; align-items: center; justify-content: center;
                    padding: 10px 28px; border-radius: 10px;
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.1);
                    color: rgba(255,255,255,0.7); font-size: 0.85rem;
                    font-family: inherit; cursor: pointer;
                    letter-spacing: 0.06em; text-decoration: none;
                    transition: all 0.25s ease;
                }
                .action-btn:hover {
                    background: rgba(255,255,255,0.12);
                    color: #fff; border-color: rgba(255,255,255,0.2);
                    transform: translateY(-1px);
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                }
                .action-btn-outline {
                    background: transparent;
                    color: rgba(255,255,255,0.4);
                    border-color: rgba(255,255,255,0.06);
                }
                .action-btn-outline:hover {
                    background: rgba(255,255,255,0.04);
                    color: rgba(255,255,255,0.7);
                }

                /* ── 하단 네비게이션 ── */
                .bottom-nav {
                    position: relative; padding: 24px 0 32px;
                    display: flex; align-items: center; gap: 12px; z-index: 10;
                }
                .nav-link {
                    color: rgba(255,255,255,0.2); font-size: 0.72rem;
                    letter-spacing: 0.05em; text-decoration: none;
                    transition: color 0.2s ease;
                }
                .nav-link:hover { color: rgba(255,255,255,0.6); }
                .nav-divider { color: rgba(255,255,255,0.1); font-size: 0.7rem; }

                /* ── 모바일 ── */
                @media (max-width: 640px) {
                    .content { padding: 90px 16px 60px; }
                    .timer-area { top: 16px; right: 16px; }
                    .timer-total, .timer-question {
                        padding: 6px 10px; gap: 6px;
                    }
                    .timer-label { font-size: 0.6rem; min-width: 40px; }
                    .timer-value { font-size: 0.85rem; min-width: 50px; }
                    .question-area { gap: 8px; }
                    .answer-panel { padding: 8px 4px; gap: 6px; }
                    .answer-btn { width: 34px; height: 34px; font-size: 0.8rem; }
                    .answer-label { font-size: 0.5rem; }
                    .nav-buttons { gap: 8px; }
                    .nav-btn { padding: 8px 14px; font-size: 0.75rem; }
                    .progress-dots { max-width: 140px; }
                    .finish-table th, .finish-table td { padding: 8px 6px; font-size: 0.7rem; }
                    .finish-actions { flex-direction: column; width: 100%; }
                    .action-btn { width: 100%; justify-content: center; }
                    .score-summary { padding: 20px 24px; }
                    .score-number { font-size: 2.4rem; }
                    .score-details { gap: 10px; }
                    .score-item { padding: 4px 10px; }
                    .review-bar { flex-direction: column; gap: 10px; padding: 8px 12px; }
                    .review-back-btn { font-size: 0.72rem; }
                    .review-correct-label { font-size: 0.55rem; }
                    .commentary-toggle-btn { padding: 6px 8px; font-size: 0.6rem; }
                    .tts-play-btn { padding: 6px 6px; font-size: 0.58rem; }
                    .tts-stop-btn { width: 24px; height: 24px; }
                    .tts-saved-badge { font-size: 0.5rem; }
                    .commentary-body { padding: 12px 14px; }
                    .commentary-text p { font-size: 0.75rem; }
                    .draw-toolbar { padding: 6px 10px; gap: 4px; }
                    .color-btn { width: 24px; height: 24px; }
                    .color-btn .color-dot { width: 12px; height: 12px; }
                    .tool-btn { width: 28px; height: 28px; }
                }
            `}</style>
        </div>
    );
}
