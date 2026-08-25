import { useState } from "react";
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
 * 부지급 사유 조항 확인은 여기 세 번째 탭으로 두지 않고 "약관 형광펜"으로 옮겼다 —
 * 청구 전 점검은 이미 두 가지 일로 꽉 차 있었고, 부지급 통지서는 앱에 접수한 사고와
 * 무관하게 받을 수 있어 "조항을 직접 찾아보는" 약관 형광펜 쪽이 성격상 더 맞다.
 */
export function ClaimCheck() {
  const [tab, setTab] = useState<Tab>("docs");

  return (
    <div className="page">
      <TopBar title="청구 전 점검" />
      <PageHero
        icon="file-text"
        eyebrow="CLAIM CHECK"
        title={"청구 전에\n두 가지만 확인해요"}
        subtitle="필요한 서류를 갖췄는지, 놓치거나 어긋난 정보가 없는지 순서대로 확인합니다."
      />
      <div className="tabs">
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
      {tab === "docs" ? <DocumentCheck embedded /> : <MistakeCheck embedded />}
    </div>
  );
}
