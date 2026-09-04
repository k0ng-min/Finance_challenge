/**
 * jsdom에 없는 브라우저 API를 최소한으로 채운다.
 *
 * 실제 브라우저에는 있고 jsdom에는 없는 것들이다. 흉내를 정교하게 만들 이유는 없다 —
 * 이 자리에서 확인하려는 건 스크롤바가 몇 픽셀인지가 아니라 "고지를 지나야 파일 선택기가
 * 열린다" 같은 흐름이라, 관측자가 아무 일도 하지 않아도 그 흐름은 그대로 검증된다.
 */
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// 시험 하나가 끝나면 그려 둔 화면을 걷어낸다. 안 하면 다음 시험에서 같은 버튼이 두 개씩
// 잡힌다. (globals: true를 쓰면 라이브러리가 알아서 걸어 주는데, 여기서는 필요한 것만
// 이름을 적어 가져오기로 해서 직접 건다.)
afterEach(cleanup);

class NoopObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}

if (!("ResizeObserver" in globalThis)) {
  (globalThis as { ResizeObserver?: unknown }).ResizeObserver = NoopObserver;
}
if (!("IntersectionObserver" in globalThis)) {
  (globalThis as { IntersectionObserver?: unknown }).IntersectionObserver = NoopObserver;
}
if (typeof window.scrollTo !== "function") {
  window.scrollTo = (() => {}) as typeof window.scrollTo;
}
