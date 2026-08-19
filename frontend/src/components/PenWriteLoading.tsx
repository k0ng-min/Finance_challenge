import { PenWriteCompass } from "./PenWriteCompass";

/**
 * 로딩 화면에서 쓰는 「보험형광펜」 손글씨 애니메이션.
 *
 * 예전에는 로딩 화면마다 3D 아이콘 하나가 좌우로 삐딱삐딱 흔들렸다. 홈 히어로에는 이미
 * 서비스 이름을 손으로 쓰고 형광펜으로 칠하는 애니메이션이 있는데, 기다리는 화면만 다른
 * 언어를 쓰고 있었다. 같은 애니메이션을 그 자리에 그대로 옮긴다.
 *
 * 시간만 다르게 잡는다. 홈은 사용자가 머무는 화면이라 천천히 써도 되지만(15초 쓰고 10초
 * 유지), 로딩은 몇 초 만에 끝나는 기다림이라 그 속도로는 형광펜이 나오기도 전에 화면이
 * 넘어간다. 여기서는 빠르게 써서 칠하고, 2초만 두었다가 흐려지며 지워진 뒤 곧바로 다시
 * 쓰기 시작한다 — 기다리는 내내 같은 동작이 반복된다.
 */
const LOADING_WRITE_DURATION = 4.5;
const LOADING_HOLD_DURATION = 2;

export function PenWriteLoading() {
  return (
    <PenWriteCompass
      className="pwc--loading"
      writeDuration={LOADING_WRITE_DURATION}
      holdDuration={LOADING_HOLD_DURATION}
    />
  );
}
