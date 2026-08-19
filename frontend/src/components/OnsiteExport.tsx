import { useRef, useState } from "react";
import { toPng } from "html-to-image";
import { Modal } from "./Modal";
import type { OnsiteDocOut, OnsitePackOut } from "../api";

/**
 * 「해외 서류 챙기기」 결과를 손에 남기는 두 가지 길.
 *
 * 이 화면은 병원·경찰서 창구 앞에 서 있는 사람이 쓴다. 그런데 정작 그 자리는 데이터가
 * 잘 안 터지고, 폰을 창구 직원에게 넘겨줘야 하는 순간도 있다. 앱을 열어야만 볼 수 있는
 * 내용이면 정작 필요한 순간에 못 쓴다.
 *
 *   · **HTML 파일** — 브라우저만 있으면 열리는 파일 하나로 저장한다. 스타일을 파일 안에
 *     넣어서 인터넷이 아예 없어도 그대로 보인다. 창구에 폰을 넘겨줄 때 이 파일만 열어
 *     주면 되고, 메신저로 보내 두면 폰이 꺼져도 남는다.
 *   · **이미지(PNG)** — 갤러리에 남기거나 메신저로 바로 보낼 때. 보험료 비교 화면의 공유
 *     카드와 같은 방식이다.
 *
 * 두 파일 모두 **현지어와 한국어를 함께** 담는다. 창구에 보여주는 물건이라 번역이 필요하지만,
 * 자기가 뭘 보여주고 있는지 모르면 안 된다. 근거 조항은 한국어 원문 그대로 인용한다 —
 * 약관 원문을 번역해 옮기면 그건 더 이상 원문이 아니다.
 */
export function OnsiteExport({
  pack, docs, typeName,
}: {
  pack: OnsitePackOut;
  docs: OnsiteDocOut[];
  typeName: string;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<null | "image" | "html">(null);
  const [failed, setFailed] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const baseName = `해외서류_${pack.country ?? "여행"}_${typeName}`.replace(/[\\/:*?"<>|]/g, "");

  function download(href: string, filename: string) {
    const a = document.createElement("a");
    a.href = href;
    a.download = filename;
    a.click();
  }

  async function saveImage() {
    if (!cardRef.current) return;
    setBusy("image");
    setFailed(false);
    try {
      const dataUrl = await toPng(cardRef.current, { pixelRatio: 2, cacheBust: true });
      download(dataUrl, `${baseName}.png`);
    } catch {
      setFailed(true);
    } finally {
      setBusy(null);
    }
  }

  function saveHtml() {
    setBusy("html");
    setFailed(false);
    try {
      const blob = new Blob([buildStandaloneHtml(pack, docs, typeName)], {
        type: "text/html;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      download(url, `${baseName}.html`);
      // 즉시 revoke하면 브라우저가 내려받기를 시작하기 전에 사라질 수 있다.
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch {
      setFailed(true);
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <button type="button" className="rank-compare-trigger" onClick={() => setOpen(true)}>
        <span>이 서류 카드를 파일로 저장</span>
      </button>

      <Modal open={open} onClose={() => setOpen(false)} title="서류 카드 저장" className="modal-card--wide">
        <p className="muted" style={{ fontSize: "0.78rem", marginTop: 0 }}>
          데이터가 없는 곳에서도 열 수 있게 파일로 저장해 두세요. 창구에 그대로 보여주면 돼요.
        </p>

        <div ref={cardRef} className="onsite-export-card">
          <p className="onsite-export-card__eyebrow">TRAVEL INSURANCE · 서류 요청 카드</p>
          <h3 className="onsite-export-card__title">
            {pack.country ?? "해외"} · {typeName}
          </h3>
          <p className="onsite-export-card__subtitle">{pack.lang_name_ko}</p>

          {pack.intro_local && <p className="onsite-export-card__intro-local">{pack.intro_local}</p>}
          <p className="onsite-export-card__intro-ko">{pack.intro_ko}</p>

          {docs.map((doc) => (
            <div key={doc.required_doc_std_id} className="onsite-export-card__doc">
              {doc.doc_name_local && (
                <p className="onsite-export-card__doc-local">{doc.doc_name_local}</p>
              )}
              <p className="onsite-export-card__doc-ko">{doc.doc_name_ko}</p>
              {doc.note && <p className="onsite-export-card__note">{doc.note}</p>}
              {doc.requirements.map((req, i) => (
                <div className="onsite-export-card__req" key={`${req.clause_id}-${i}`}>
                  {req.label_local && <p className="onsite-export-card__req-local">{req.label_local}</p>}
                  <p className="onsite-export-card__req-ko">{req.label_ko}</p>
                  {req.clause_quote && (
                    <p className="onsite-export-card__quote">
                      <span>{req.insurer_name} {req.clause_article_no}</span>
                      {req.clause_quote}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="onsite-export-actions">
          <button type="button" className="btn-primary" disabled={busy !== null} onClick={saveHtml}>
            {busy === "html" ? "만드는 중..." : "HTML 파일로 저장"}
          </button>
          <button type="button" className="btn-secondary" disabled={busy !== null} onClick={saveImage}>
            {busy === "image" ? "만드는 중..." : "이미지로 저장"}
          </button>
        </div>
        {failed && (
          <p className="error-box" style={{ marginTop: 8 }}>
            파일을 만들지 못했어요. 다시 시도해 주세요.
          </p>
        )}
      </Modal>
    </>
  );
}

/** HTML 특수문자를 그대로 글자로 보이게 한다 — 약관 원문에 &나 <가 섞여 있어도 깨지지 않게. */
function esc(value: string | null | undefined): string {
  return (value ?? "").replace(/[&<>"']/g, (ch) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch] as string
  ));
}

/**
 * 파일 하나로 끝나는 HTML을 만든다.
 *
 * 스타일을 문서 안에 넣고 바깥 리소스를 하나도 참조하지 않는다 — 비행기모드에서 열어도,
 * 몇 달 뒤 이 앱이 없어도 그대로 열린다. 색은 흰 배경 기준으로 고정한다(다크 모드에서
 * 저장한 파일이 창구 직원 폰에서 검게 나오면 곤란하다).
 */
function buildStandaloneHtml(pack: OnsitePackOut, docs: OnsiteDocOut[], typeName: string): string {
  const docBlocks = docs.map((doc) => {
    const reqs = doc.requirements.map((req) => `
        <div class="req">
          ${req.label_local ? `<p class="req-local">${esc(req.label_local)}</p>` : ""}
          <p class="req-ko">${esc(req.label_ko)}</p>
          ${req.clause_quote ? `
          <blockquote>
            <span class="src">${esc(req.insurer_name)} ${esc(req.clause_article_no)}</span>
            ${esc(req.clause_quote)}
          </blockquote>` : ""}
        </div>`).join("");
    return `
      <section class="doc${doc.acquire_location === "현지only" ? " urgent" : ""}">
        ${doc.doc_name_local ? `<p class="doc-local">${esc(doc.doc_name_local)}</p>` : ""}
        <p class="doc-ko">${esc(doc.doc_name_ko)}</p>
        ${doc.acquire_location === "현지only" ? `<p class="badge">귀국하면 못 받아요</p>` : ""}
        ${doc.note ? `<p class="note">${esc(doc.note)}</p>` : ""}
        ${reqs}
      </section>`;
  }).join("");

  return `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(pack.country ?? "해외")} 서류 요청 카드 · ${esc(typeName)}</title>
<style>
  :root { color-scheme: light; }
  body { margin: 0; padding: 20px 16px 40px; background: #f4f7fc; color: #1f2a3d;
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
         line-height: 1.6; }
  .wrap { max-width: 640px; margin: 0 auto; }
  .eyebrow { margin: 0 0 6px; font-size: 0.7rem; font-weight: 800; letter-spacing: 1.5px; color: #4b84ec; }
  h1 { margin: 0 0 4px; font-size: 1.3rem; }
  .lang { margin: 0 0 18px; font-size: 0.8rem; color: #8592a8; }
  .intro { background: #fff; border: 1px solid #e2eaf7; border-radius: 14px; padding: 16px; margin-bottom: 18px; }
  .intro-local { margin: 0 0 6px; font-size: 1.02rem; font-weight: 700; }
  .intro-ko { margin: 0; font-size: 0.85rem; color: #5a6880; }
  .doc { background: #fff; border: 1px solid #e2eaf7; border-radius: 14px; padding: 16px; margin-bottom: 12px; }
  .doc.urgent { border-color: #f5c6c6; background: #fffafa; }
  .doc-local { margin: 0 0 2px; font-size: 1.02rem; font-weight: 700; }
  .doc-ko { margin: 0; font-size: 0.84rem; color: #5a6880; }
  .badge { display: inline-block; margin: 8px 0 0; padding: 3px 9px; border-radius: 999px;
           background: #fdecec; color: #c0392b; font-size: 0.7rem; font-weight: 700; }
  .note { margin: 8px 0 0; font-size: 0.8rem; color: #5a6880; }
  .req { margin-top: 12px; padding-top: 12px; border-top: 1px solid #eef4fd; }
  .req-local { margin: 0 0 2px; font-size: 0.92rem; font-weight: 600; }
  .req-ko { margin: 0; font-size: 0.8rem; color: #5a6880; }
  blockquote { margin: 8px 0 0; padding: 10px 12px; background: #f7faff; border-left: 3px solid #b9d0f5;
               border-radius: 0 8px 8px 0; font-size: 0.76rem; color: #45536b; }
  .src { display: block; margin-bottom: 4px; font-size: 0.68rem; font-weight: 700; color: #4b84ec; }
  footer { margin-top: 20px; font-size: 0.7rem; color: #8592a8; }
</style>
</head>
<body>
  <div class="wrap">
    <p class="eyebrow">TRAVEL INSURANCE · 서류 요청 카드</p>
    <h1>${esc(pack.country ?? "해외")} · ${esc(typeName)}</h1>
    <p class="lang">${esc(pack.lang_name_ko)}</p>
    <div class="intro">
      ${pack.intro_local ? `<p class="intro-local">${esc(pack.intro_local)}</p>` : ""}
      <p class="intro-ko">${esc(pack.intro_ko)}</p>
    </div>
    ${docBlocks}
    <footer>인용된 조항은 각 보험사 약관 원문 그대로입니다. 실제 지급 여부는 보험사 심사에 따라 정해집니다.</footer>
  </div>
</body>
</html>`;
}
