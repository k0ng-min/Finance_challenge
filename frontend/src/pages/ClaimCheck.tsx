import { useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { DocumentCheck } from "./DocumentCheck";
import { MistakeCheck } from "./MistakeCheck";

type Tab = "docs" | "mistakes";

/**
 * 서류 체크와 실수 방지 점검을 한 화면에 합쳤다.
 *
 * 둘 다 "같은 사고 한 건을 청구하기 전에 확인하는 일"이라 화면을 나눠 둘 이유가 없었고,
 * 홈에서 칸을 두 개 잡아먹고 있었다. 탭으로 묶고 남은 자리는 보험료 비교공시에 내줬다.
 *
 * 부지급 사유 조항 확인은 여기 세 번째 탭으로 두지 않고 "보험 형광펜"으로 옮겼다 —
 * 청구 전 점검은 이미 두 가지 일로 꽉 차 있었고, 부지급 통지서는 앱에 접수한 사고와
 * 무관하게 받을 수 있어 "조항을 직접 찾아보는" 보험 형광펜 쪽이 성격상 더 맞다.
 */
export function ClaimCheck() {
  // ?tab=mistakes로 들어오면 실수 방지부터 편다. 합치기 전 주소인 /mistakes가 여기로
  // 넘어오는데(App.tsx), 그냥 넘기면 "실수 방지 보러 왔는데 서류 체크가 열리는" 셈이 된다 —
  // 옛 링크나 북마크를 눌러도 원래 보려던 쪽이 나와야 한다.
  const [params] = useSearchParams();
  const [tab, setTab] = useState<Tab>(params.get("tab") === "mistakes" ? "mistakes" : "docs");
  const tabsRef = useRef<HTMLDivElement>(null);

  // 서류 체크 맨 아래 "실수 방지 점검하러 가기"는 원래 /mistakes로 navigate했는데, 두
  // 화면을 여기 탭으로 합치면서 그 경로가 /checklist로 되돌아오게 됐다(App.tsx). 결과는
  // 같은 화면을 다시 마운트하는 것뿐 — 탭은 첫 번째("서류 체크")로 초기화되고, 사용자
  // 눈에는 아무 일도 일어나지 않는다. 이동 대신 탭을 바꾸고 그 자리로 올려준다.
  function goToMistakes() {
    setTab("mistakes");
    tabsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="page">
      <TopBar title="청구 전 점검" />
      <PageHero
        icon="file-text"
        eyebrow="CLAIM CHECK"
        title={"청구 전에\n두 가지만 확인해요"}
        subtitle="필요한 서류를 갖췄는지, 놓치거나 어긋난 정보가 없는지 순서대로 확인합니다."
      />
      <div className="tabs" ref={tabsRef}>
        <button
          type="button"
          className={`tab${tab === "docs" ? " tab--active" : ""}`}
          onClick={() => setTab("docs")}
        >
          서류 체크
        </button>
        <button
          type="button"
          className={`tab${tab === "mistakes" ? " tab--active" : ""}`}
          onClick={() => setTab("mistakes")}
        >
          실수 방지
        </button>
      </div>
      {tab === "docs"
        ? <DocumentCheck embedded onNextStep={goToMistakes} />
        : <MistakeCheck embedded />}
    </div>
  );
}
