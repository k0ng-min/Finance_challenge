/**
 * 테스트 설정을 vite.config.ts와 따로 둔다.
 *
 * 같이 두면 tsc가 빌드할 때 vitest가 딸려 온 자기 vite 사본과 프로젝트의 vite 8이
 * 부딪혀(rollup ↔ rolldown 플러그인 타입) 빌드가 통째로 깨진다. tsconfig.node.json이
 * 보는 파일은 vite.config.ts 하나뿐이라, 이 파일로 옮기면 빌드는 건드리지 않으면서
 * 테스트는 그대로 돌아간다.
 *
 * 테스트는 화면을 실제로 그려 놓고 사람이 하듯 눌러 본다. 지키려는 성질(고지를 지나지
 * 않으면 파일 선택기가 열리지 않는다)이 컴포넌트 안쪽 구현이 아니라 사용자가 겪는
 * 흐름이라, 렌더링 없이 함수만 불러서는 확인할 수 없다.
 */
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
