import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
    title: "공잘알 - 공무원 시험 AI",
    description: "공무원 시험, 잘 알려주는 AI",
    manifest: "/manifest.json",
    appleWebApp: {
        capable: true,
        statusBarStyle: "default",
        title: "공잘알",
    },
    formatDetection: {
        telephone: false,
    },
    openGraph: {
        type: "website",
        siteName: "공잘알",
        title: "공잘알 - 공무원 시험 AI",
        description: "공무원 시험, 잘 알려주는 AI",
    },
    twitter: {
        card: "summary",
        title: "공잘알 - 공무원 시험 AI",
        description: "공무원 시험, 잘 알려주는 AI",
    },
    icons: {
        icon: [
            { url: "/icons/icon-192x192.svg", sizes: "192x192", type: "image/svg+xml" },
            { url: "/icons/icon-512x512.svg", sizes: "512x512", type: "image/svg+xml" },
        ],
        apple: [
            { url: "/icons/icon-192x192.svg", sizes: "192x192", type: "image/svg+xml" },
        ],
    },
};

export const viewport: Viewport = {
    themeColor: "#000000",
    width: "device-width",
    initialScale: 1,
    maximumScale: 5,
    userScalable: true,
    viewportFit: "cover",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="ko">
            <head>
                <link rel="manifest" href="/manifest.json" />
                <meta name="application-name" content="공잘알" />
                <meta name="apple-mobile-web-app-capable" content="yes" />
                <meta name="apple-mobile-web-app-status-bar-style" content="default" />
                <meta name="apple-mobile-web-app-title" content="공잘알" />
                <meta name="mobile-web-app-capable" content="yes" />
            </head>
            <body style={{ margin: 0, padding: 0 }}>{children}</body>
        </html>
    );
}

