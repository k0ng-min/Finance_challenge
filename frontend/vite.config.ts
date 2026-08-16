import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // 「현지에서」 화면은 해외 현지에서 여는 물건이다. 로밍이 없거나 백엔드가 잠들어
    // (Render 무료 플랜 cold start 30~60초) 정작 필요한 순간에 앱이 안 열리면 소용이 없다.
    // 그래서 앱 셸을 미리 캐시하고, 현지 대응 팩 응답은 NetworkFirst로 캐시해 둔다.
    //
    // 범위를 오프라인 "열람"으로 한정한다. 오프라인 중 쓰기(서류 상태 변경 등)는 동기화
    // 충돌이라는 별개 문제라 이번 범위 밖이다.
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', '3d/*.webp'],
      manifest: {
        name: '약관 형광펜 — 근거 기반 여행자보험 AI',
        short_name: '약관형광펜',
        description: '6개 손해보험사 약관 원문을 근거로 여행 전 비교부터 사고 후 청구까지.',
        theme_color: '#4b84ec',
        background_color: '#f8fbff',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: '/favicon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' },
        ],
      },
      workbox: {
        // 3D 아이콘(webp)까지 미리 받아둔다 — 오프라인에서 화면이 글자만 남지 않게.
        globPatterns: ['**/*.{js,css,html,svg,webp,woff2}'],
        navigateFallback: '/index.html',
        runtimeCaching: [
          {
            // 현지 대응 팩. 온라인이면 최신을, 오프라인이면 마지막 응답을 쓴다.
            // 응답에 generated_at이 있어 화면이 "언제 기준"인지 정직하게 밝힐 수 있다.
            urlPattern: /\/(trips\/\d+\/onsite|onsite)(\?.*)?$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'onsite-pack',
              networkTimeoutSeconds: 8,
              expiration: { maxEntries: 24, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [200] },
            },
          },
        ],
      },
    }),
  ],
})
