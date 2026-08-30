import { PenWriteLoading } from "./PenWriteLoading";
import type { BootPhase } from "../context/AppContext";

/**
 * 앱을 처음 열 때 서버에 닿기까지 보여주는 화면.
 *
 * 예전에는 여기가 "여행자보험 AI를 준비하고 있어요..." 한 줄이었다. 무료 호스팅(Render)은
 * 15분간 요청이 없으면 서버가 잠들고 다음 방문자가 기상을 30~60초 기다리는데, 그 시간 내내
 * 같은 문구가 멈춰 있으니 처음 온 사람은 고장으로 읽고 창을 닫았다. 기다리는 것 자체는
 * 무료 요금제의 성질이라 없앨 수 없으니, 대신 무슨 일이 벌어지고 있고 얼마나 걸리는지를
 * 정확히 말해 준다 — 사람은 이유를 아는 기다림은 견딘다.
 */
export function BootScreen({
  phase,
  seconds,
  onRetry,
}: {
  phase: BootPhase;
  seconds: number;
  onRetry: () => void;
}) {
  if (phase === "failed") {
    return (
      <div className="boot-screen">
        <p className="boot-screen__title">서버에 연결하지 못했어요</p>
        <p className="boot-screen__desc">
          잠시 네트워크가 불안정했거나, 서버가 아직 준비되지 않았을 수 있어요.
          <br />
          다시 시도해 주세요.
        </p>
        <button type="button" className="boot-screen__retry" onClick={onRetry}>
          다시 시도
        </button>
      </div>
    );
  }

  const waking = phase === "waking";
  // 기상은 보통 30~60초다. 60초를 100%로 잡아 얼마나 남았는지 감을 주되, 60초를 넘겨도
  // 막대가 가득 찬 채 계속 기다리게 둔다 — 실제로 그때 도착하는 경우가 있어서,
  // 막대가 찼다고 실패라고 말해 버리면 거짓말이 된다.
  const progress = Math.min(100, Math.round((seconds / 60) * 100));

  return (
    <div className="boot-screen">
      <PenWriteLoading />
      <p className="boot-screen__title">
        {waking ? "잠들어 있던 서버를 깨우는 중이에요" : "여행자보험 AI를 준비하고 있어요..."}
      </p>
      {waking && (
        <>
          <p className="boot-screen__desc">
            무료 서버라 한동안 접속이 없으면 잠들어요. 처음 열 때 한 번만 기다리면 되고,
            그다음부터는 바로 열립니다.
          </p>
          <div
            className="boot-screen__bar"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
            aria-label="서버 준비 중"
          >
            <div className="boot-screen__bar-fill" style={{ width: `${progress}%` }} />
          </div>
          <p className="boot-screen__elapsed">{seconds}초 경과 · 보통 30~60초 걸려요</p>
        </>
      )}
    </div>
  );
}
