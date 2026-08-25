import { useState } from "react";
import type { ExternalPolicyKind } from "../api";
import { DateTimeField } from "./DateTimeField";
import { InsurerPicker } from "./InsurerPicker";

/** 실손 가입시기는 과거만 의미가 있어서 오늘 이후는 못 고르게 막는다. */
function todayYmd() {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** 기존보험 선택 UI. 내 보험·여행 준비·사고 접수 세 화면이 같이 쓴다. */

export const KIND_LABELS: Record<ExternalPolicyKind, string> = {
  MEDICAL_INDEMNITY: "실손의료비(실비)",
  ACCIDENT: "상해보험",
  DAILY_LIABILITY: "일상생활배상책임",
  DRIVER: "운전자보험",
  OTHER: "그 외",
};

export interface PickedPolicy {
  kind: ExternalPolicyKind;
  insurer_name_raw?: string | null;
  enrolled_ym?: string | null;
}

export function ExternalPolicyPicker({
  value, onChange,
}: {
  value: PickedPolicy[];
  onChange: (next: PickedPolicy[]) => void;
}) {
  const [insurer, setInsurer] = useState("");

  function toggle(kind: ExternalPolicyKind) {
    const exists = value.find((v) => v.kind === kind);
    if (exists) {
      onChange(value.filter((v) => v.kind !== kind));
    } else {
      onChange([...value, { kind, insurer_name_raw: insurer || null, enrolled_ym: null }]);
    }
  }

  function setYm(kind: ExternalPolicyKind, ym: string) {
    onChange(value.map((v) => (v.kind === kind ? { ...v, enrolled_ym: ym || null } : v)));
  }

  const indemnity = value.find((v) => v.kind === "MEDICAL_INDEMNITY");

  return (
    <>
      <p className="page-desc">
        이미 들고 계신 보험을 골라주세요. 겹치는 담보와 비는 담보를 약관 근거와 함께 알려드려요.
      </p>

      {/* 이 프로젝트에는 .chip 클래스가 없다 — PremiumCalc.tsx의 보험사 토글칩과 같은
          .calc-chips / .premium-chip(--on) 조합을 재사용한다. */}
      <div className="field-block">
        <span className="field-block__label">어떤 보험이 있나요? (여러 개 고를 수 있어요)</span>
        <div className="calc-chips">
          {(Object.keys(KIND_LABELS) as ExternalPolicyKind[]).map((kind) => {
            const on = value.some((v) => v.kind === kind);
            return (
              <button
                key={kind}
                type="button"
                className={`premium-chip${on ? " premium-chip--on" : ""}`}
                onClick={() => toggle(kind)}
              >
                {KIND_LABELS[kind]}
              </button>
            );
          })}
        </div>
      </div>

      {/* 실손만 가입시기를 묻는다 — 실손은 2009년 표준화 이후 보장구조가 보험사별로 같아서
          가입시기 하나로 세대(1~4세대)가 정해지고, 세대가 보장구조를 결정한다. */}
      {indemnity && (
        <div className="indemnity-when">
          <DateTimeField
            label="실손은 언제 가입하셨나요?"
            mode="month"
            value={indemnity.enrolled_ym ?? ""}
            onChange={(v) => setYm("MEDICAL_INDEMNITY", v)}
            placeholder="기억나는 대로 골라주세요"
            minDate="1990-01-01"
            maxDate={todayYmd()}
            clearable
            icon="🗓️"
          />
          <p className="indemnity-when__hint">
            가입한 달만 알면 실손 세대(1~4세대)가 정해져요. 세대에 따라 보장구조가 달라서
            여행자보험과 겹치는 부분이 바뀝니다. <strong>모르면 비워두셔도 괜찮아요.</strong>
          </p>
        </div>
      )}

      <div className="field-block">
        <span className="field-block__label">보험사 (모르면 비워두세요)</span>
        <InsurerPicker value={insurer} onChange={setInsurer} />
      </div>
    </>
  );
}
