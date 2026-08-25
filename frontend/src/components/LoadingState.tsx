import { PenWriteLoading } from "./PenWriteLoading";

/** 화면 전체를 기다리게 하는 짧은 로딩(앱 부팅, 라우트 전환, OAuth 콜백 등).
 * LoadingScreen과 같은 손글씨 애니메이션을 써서, 어느 화면에서 기다리든 같은 그림이 보인다. */
export function LoadingState({ label = "불러오는 중이에요..." }: { label?: string }) {
  return (
    <div className="loading-state">
      <PenWriteLoading />
      <p>{label}</p>
    </div>
  );
}
