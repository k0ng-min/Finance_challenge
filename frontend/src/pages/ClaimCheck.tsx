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
