import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "공잘알 채팅",
    description: "ChatGPT 스타일 챗봇 PWA",
};

export default function ChatLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <>{children}</>;
}
