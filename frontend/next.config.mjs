import withPWA from 'next-pwa';

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  typedRoutes: true, // experimental에서 이동됨
  // Turbopack 설정 (Next.js 16에서 기본 활성화)
  turbopack: {
    root: process.cwd(), // workspace root 경고 해결
  },
  // 반응형 디자인을 위한 이미지 최적화 설정
  images: {
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60,
    dangerouslyAllowSVG: true,
    contentDispositionType: 'attachment',
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  // 반응형 컴포넌트를 위한 컴파일러 옵션
  compiler: {
    // CSS 모듈 최적화
    styledComponents: false,
  },
  // 모바일 최적화를 위한 설정
  poweredByHeader: false,
  compress: true,
  // 반응형 라우팅 최적화
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin'
          },
        ],
      },
    ];
  },
};

const pwaConfig = withPWA({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: false, // 개발 환경에서도 PWA 활성화
  // 주의: 개발 환경에서 Service Worker가 활성화되면 코드 변경이 즉시 반영되지 않을 수 있습니다.
  // 개발 중 Service Worker 문제가 발생하면 브라우저 개발자 도구 > Application > Service Workers에서 Unregister 하세요.
  fallbacks: {
    document: '/_offline',
  },
  buildExcludes: [/middleware-manifest\.json$/],
  runtimeCaching: [
    {
      urlPattern: /^https?.*/,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'offlineCache',
        expiration: {
          maxEntries: 200,
        },
      },
    },
  ],
});

export default pwaConfig(nextConfig);


