import { useRef, useState } from "react";
import { api, userMessage, type ChecklistOut, type DocCheckOut, type DocVerifyOut } from "../api";
import { Modal } from "./Modal";

/**
 * 서류 사진을 올려 번역·요건 대조를 받는다.
 *
 * 사진은 어디까지나 거들기다 — 상태를 직접 고르는 기존 방법은 그대로 두고, 외국어라
 * 이게 맞는 서류인지 모르겠을 때만 쓰면 된다. 그래서 표 안에서는 상태 선택 옆에 붙는
 * 작은 아이콘 버튼 하나로만 존재한다(예전엔 상태 선택과 같은 크기의 알약이 아래 한 줄을
 * 더 차지해서, 행마다 반복되며 정작 골라야 할 상태보다 더 눈에 띄었다).
 *
 * 결과는 두 칸으로 나눠 보여준다. 약관 조항을 근거로 든 것과, 실무상 흔히 보는 것을
 * 섞으면 사용자가 어느 쪽이 계약상 요건인지 구분할 수 없다.
 */

/**
 * 카메라로 바로 찍을 만한 기기인지.
 *
 * pointer: coarse 하나만 보면 놓치는 기기가 있다(마우스를 연결한 태블릿, 일부 브라우저).
 * 세 신호를 OR로 묶는다 — 잘못 참이 나와도 손해가 없다. 선택지에 "앨범에서 고르기"가 늘
 * 같이 있어서 평소 파일 선택으로 그대로 이어진다.
 */
function canTakePhoto() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(pointer: coarse)").matches ||
    window.matchMedia("(any-pointer: coarse)").matches ||
    navigator.maxTouchPoints > 0
  );
}

export function DocPhotoCheck({
  incidentId, docStdId, onChecklist,
}: {
  incidentId: number;
  docStdId: number;
  onChecklist: (next: ChecklistOut) => void;
}) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(false);
  const [result, setResult] = useState<DocVerifyOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.verifyDocumentPhoto(incidentId, docStdId, file);
      setResult(res);
      onChecklist(res.checklist);
    } catch (err) {
      setError(userMessage(err, "사진을 확인하지 못했어요. 다시 시도해 주세요."));
    } finally {
      setBusy(false);
      // 같은 파일을 다시 골라도 change가 뜨도록 비워둔다.
      if (cameraRef.current) cameraRef.current.value = "";
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function start() {
    // 휴대폰이면 "찍기"와 "고르기"를 직접 묻는다. accept에 PDF를 섞으면 기기에 따라
    // 카메라 대신 문서 선택기가 열려버려서, 촬영은 전용 입력(capture)으로 분리했다.
    if (canTakePhoto()) setAsking(true);
    else fileRef.current?.click();
  }

  return (
    <>
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <input
        ref={fileRef}
        type="file"
        accept="image/*,application/pdf"
        hidden
        onChange={(e) => handleFile(e.target.files?.[0])}
      />

      <button
        type="button"
        className={`doc-photo-btn${busy ? " is-busy" : ""}`}
        disabled={busy}
        onClick={start}
        title="사진으로 확인하기"
        aria-label="서류 사진으로 확인하기"
      >
        {busy ? <span className="doc-photo-btn__spin" aria-hidden /> : <CameraIcon />}
      </button>

      {asking && (
        <Modal open title="서류 사진" onClose={() => setAsking(false)}>
          <div className="doc-photo-choice">
            <button type="button" onClick={() => { setAsking(false); cameraRef.current?.click(); }}>
              <CameraIcon />
              <span><strong>사진 찍기</strong><em>지금 서류를 촬영해요</em></span>
            </button>
            <button type="button" onClick={() => { setAsking(false); fileRef.current?.click(); }}>
              <AlbumIcon />
              <span><strong>앨범에서 고르기</strong><em>이미 찍어둔 사진·PDF</em></span>
            </button>
          </div>
        </Modal>
      )}

      {error && (
        <Modal open title="사진 확인" onClose={() => setError(null)}>
          <p className="doc-verify__message">{error}</p>
        </Modal>
      )}

      {result && (
        <Modal open title={result.doc_name} onClose={() => setResult(null)}>
          <div className="doc-verify">
            <p className={`doc-verify__message${result.applied_status ? "" : " doc-verify__message--hold"}`}>
              {result.message}
            </p>

            {result.readable && (result.language || result.detected_doc_type) && (
              <p className="doc-verify__meta">
                {[result.language, result.detected_doc_type].filter(Boolean).join(" · ")}(으)로 보여요
              </p>
            )}

            {result.translation && (
              <section className="doc-verify__block">
                <h4>무슨 내용인가요</h4>
                <p className="doc-verify__translation">{result.translation}</p>
              </section>
            )}

            {result.grounded.length > 0 && (
              <section className="doc-verify__block">
                <h4>약관이 요구하는 것</h4>
                <CheckList items={result.grounded} showClause />
              </section>
            )}

            {result.practical.length > 0 && (
              <section className="doc-verify__block">
                <h4>
                  일반적으로 확인하는 것
                  <span className="doc-verify__nobasis">약관 근거는 아니에요</span>
                </h4>
                <CheckList items={result.practical} />
              </section>
            )}

            <p className="doc-verify__privacy">
              올린 사진과 번역 내용은 저장하지 않아요. 이 창을 닫으면 사라집니다.
            </p>
          </div>
        </Modal>
      )}
    </>
  );
}

function CameraIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  );
}

function AlbumIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <path d="M21 15l-5-5L5 21" />
    </svg>
  );
}

function CheckList({ items, showClause = false }: { items: DocCheckOut[]; showClause?: boolean }) {
  return (
    <ul className="doc-check-list">
      {items.map((c) => (
        <li key={c.code} className={c.found ? "is-found" : "is-missing"}>
          <span className="doc-check-list__mark" aria-hidden>{c.found ? "✓" : "!"}</span>
          <div>
            <strong>{c.label}</strong>
            <span className="doc-check-list__state">{c.found ? "확인됐어요" : "안 보여요"}</span>
            {c.quote && <p className="doc-check-list__quote">서류에서: “{c.quote}”</p>}
            {showClause && c.clause_text && (
              <p className="doc-check-list__clause">
                {c.clause_article_no && <em>{c.clause_article_no}</em>}
                “…{c.clause_text}…”
              </p>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
