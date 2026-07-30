import { useState } from "react";

export interface ConsentState {
  agreeTerms: boolean;
  agreePrivacy: boolean;
  agreeAge14: boolean;
  agreeMarketing: boolean;
}

export const EMPTY_CONSENT: ConsentState = {
  agreeTerms: false,
  agreePrivacy: false,
  agreeAge14: false,
  agreeMarketing: false,
};

export function allRequiredAgreed(c: ConsentState) {
  return c.agreeTerms && c.agreePrivacy && c.agreeAge14;
}

const TERMS_TEXT = `제1조(목적)
이 약관은 '여행자보험 전 생애주기 AI'(이하 '서비스')가 제공하는 여행자보험 비교, 가입 전 점검, 사고 후 청구 검토 도움 기능의 이용 조건을 정합니다.

제2조(서비스의 성격)
서비스는 6개 보험사의 실제 약관 원문을 근거로 정보를 제공하는 참고용 도구이며, 보험 가입을 대행하거나 보험금 지급을 보장하지 않습니다. 최종 가입·청구 판단은 반드시 해당 보험사 확인을 거쳐야 합니다.

제3조(회원가입)
이용자는 이메일 또는 소셜 계정으로 가입할 수 있으며, 로그인 없이 게스트로도 대부분의 기능을 이용할 수 있습니다.

제4조(이용자의 의무)
사고·여행 정보를 사실과 다르게 입력하거나, 타인의 계정을 무단으로 사용해서는 안 됩니다.

제5조(면책)
서비스는 2026 금융 AI 챌린지 프로젝트로 제공되며, 실제 보험금 지급 여부는 각 보험사의 최종 심사에 따릅니다.`;

const PRIVACY_TEXT = `1. 수집 항목
이메일, 비밀번호(암호화 저장), 닉네임 — 소셜 로그인 시 제공자가 전달하는 이메일·식별자 포함

2. 수집 목적
회원 식별 및 로그인, 여행·보험·사고 정보 저장과 재방문 시 불러오기

3. 보유 및 이용 기간
회원 탈퇴 시까지 (탈퇴 즉시 파기)

4. 동의 거부 권리 및 불이익
동의를 거부할 수 있으며, 이 경우 이메일 회원가입은 이용할 수 없지만 게스트로는 계속 이용할 수 있습니다.`;

const MARKETING_TEXT = `신규 기능, 약관 개정 등 서비스 관련 소식을 이메일로 받아보실 수 있습니다. 언제든 계정에서 수신을 거부할 수 있어요.`;

function ConsentRow({
  label, required, checked, onToggle, detail,
}: {
  label: string;
  required: boolean;
  checked: boolean;
  onToggle: () => void;
  detail: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="consent-row">
      <label className="checkbox-label consent-row__head">
        <input type="checkbox" checked={checked} onChange={onToggle} />
        <span>
          <strong className={required ? "consent-required" : "consent-optional"}>
            {required ? "[필수]" : "[선택]"}
          </strong>{" "}
          {label}
        </span>
        <button
          type="button"
          className="consent-row__toggle"
          onClick={(e) => {
            e.preventDefault();
            setOpen((v) => !v);
          }}
        >
          {open ? "접기" : "보기"}
        </button>
      </label>
      {open && <p className="consent-detail">{detail}</p>}
    </div>
  );
}

export function TermsConsent({ value, onChange }: { value: ConsentState; onChange: (c: ConsentState) => void }) {
  const allChecked = value.agreeTerms && value.agreePrivacy && value.agreeAge14 && value.agreeMarketing;

  function toggleAll() {
    const next = !allChecked;
    onChange({ agreeTerms: next, agreePrivacy: next, agreeAge14: next, agreeMarketing: next });
  }

  return (
    <div className="consent-box">
      <label className="checkbox-label consent-row__head consent-row__all">
        <input type="checkbox" checked={allChecked} onChange={toggleAll} />
        <span><strong>전체 동의</strong></span>
      </label>
      <div className="consent-box__divider" />
      <ConsentRow
        label="서비스 이용약관 동의"
        required
        checked={value.agreeTerms}
        onToggle={() => onChange({ ...value, agreeTerms: !value.agreeTerms })}
        detail={TERMS_TEXT}
      />
      <ConsentRow
        label="개인정보 수집·이용 동의"
        required
        checked={value.agreePrivacy}
        onToggle={() => onChange({ ...value, agreePrivacy: !value.agreePrivacy })}
        detail={PRIVACY_TEXT}
      />
      <label className="checkbox-label consent-row__head">
        <input
          type="checkbox"
          checked={value.agreeAge14}
          onChange={() => onChange({ ...value, agreeAge14: !value.agreeAge14 })}
        />
        <span><strong className="consent-required">[필수]</strong> 만 14세 이상입니다</span>
      </label>
      <ConsentRow
        label="마케팅 정보 수신 동의"
        required={false}
        checked={value.agreeMarketing}
        onToggle={() => onChange({ ...value, agreeMarketing: !value.agreeMarketing })}
        detail={MARKETING_TEXT}
      />
    </div>
  );
}
