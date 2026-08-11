import { useState } from "react";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { DocumentCheck } from "./DocumentCheck";
import { MistakeCheck } from "./MistakeCheck";
import { RejectionClauseCheck } from "./RejectionClauseCheck";

type Tab = "docs" | "mistakes" | "rejection";

/**
 * 서류 체크·실수 방지 점검·부지급 사유 조항 확인을 한 화면에 합쳤다.
 *
 * 셋 다 "같은 사고 한 건을 청구 앞뒤로 확인하는 일"이라 화면을 나눠 둘 이유가 없었고,
 * 홈에서 칸을 여러 개 잡아먹을 이유도 없었다. 탭으로 묶는다.
 */
export function ClaimCheck() {
  const [tab, setTab] = useState<Tab>("docs");

  return (
    <div className="page">
      <TopBar title="청구 전 점검" />
      <PageHero
        icon="file-text"
        eyebrow="CLAIM CHECK"
        title={"청구 앞뒤로\n확인해요"}
        subtitle="필요한 서류를 갖췄는지, 놓치거나 어긋난 정보가 없는지, 부지급 통지를 받았다면 인용된 조항 원문까지 확인합니다."
      />
      <div className="tabs" style={{ flexWrap: "wrap" }}>
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
        <button
          type="button"
          className={`tab${tab === "rejection" ? " tab--active" : ""}`}
          onClick={() => setTab("rejection")}
        >
          부지급 사유 확인
        </button>
      </div>
      {tab === "docs" && <DocumentCheck embedded />}
      {tab === "mistakes" && <MistakeCheck embedded />}
      {tab === "rejection" && <RejectionClauseCheck />}
    </div>
  );
}
