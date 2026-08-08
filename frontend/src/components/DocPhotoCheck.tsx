import { useRef, useState } from "react";
import { api, userMessage, type ChecklistOut, type DocCheckOut, type DocVerifyOut } from "../api";
import { Modal } from "./Modal";

/**
 * 서류 사진을 올려 번역·요건 대조를 받는다.
 *
 * 사진은 어디까지나 거들기다 — 상태를 직접 고르는 기존 방법은 그대로 두고, 외국어라
 * 이게 맞는 서류인지 모르겠을 때만 쓰면 된다. 그래서 이 버튼은 표 안에서 작게 둔다.
 *
 * 결과는 두 칸으로 나눠 보여준다. 약관 조항을 근거로 든 것과, 실무상 흔히 보는 것을
 * 섞으면 사용자가 어느 쪽이 계약상 요건인지 구분할 수 없다.
 */
export function DocPhotoCheck({
  incidentId, docStdId, onChecklist,
}: {
  incidentId: number;
  docStdId: number;
  onChecklist: (next: ChecklistOut) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
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
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*,application/pdf"
        hidden
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <button
        type="button"
        className="doc-photo-btn"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
      >
        {busy ? "읽는 중…" : "사진으로 확인"}
      </button>

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
