import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { api, type OnsitePackOut, type OnsiteDocOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { PickerField } from "../components/PickerField";
import { Icon3D } from "../components/Icon3D";
import { LoadingState } from "../components/LoadingState";
import { OnsiteExport } from "../components/OnsiteExport";
import { COUNTRIES } from "../data/countries";

const LOCAL_ONLY = "현지only";

/**
 * 「해외 서류 챙기기」 — 해외 현지에 서 있는 사람이 쓰는 화면.
 *
 * 이 서비스의 생애주기는 여행 전 → 사고 접수 → 청구 준비 → 부지급 후로 이어지는데,
 * 정작 청구 결과가 결정되는 **현지에서의 몇 시간**이 비어 있었다. 해외에서 부지급이
 * 나는 흔한 이유는 담보가 없어서가 아니라, 약관이 요구하는 형식을 모른 채 영수증만
 * 받아오기 때문이다. 귀국하면 그 서류는 영영 못 받는다.
 *
 * 화면은 세 단이다.
 *   1단 귀국하면 못 받는 서류(현지only) + 연결된 사고가 있으면 진행률
 *   2단 사고유형을 고르면 나오는 현지어 서류 요청 카드 — 창구에 그대로 보여준다
 *   3단 오프라인 안내(서비스워커가 이 응답을 캐시한다)
 *
 * 현지어는 언제나 한국어와 병기한다. 창구에 보여주는 물건이라 번역이 붙지만, 사용자가
 * 자기가 뭘 보여주고 있는지 모르면 안 된다. 근거 조항 원문은 번역하지 않는다.
 */
export function Onsite() {
  const { tripId } = useApp();
  const [country, setCountry] = useState("");
  const [pack, setPack] = useState<OnsitePackOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeType, setActiveType] = useState<number | null>(null);
  const [offline, setOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  // 여행이 있으면 그 여행 기준으로, 없으면 고른 나라 기준으로 불러온다.
  useEffect(() => {
    if (!tripId && !country) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    const load = tripId ? api.getTripOnsitePack(tripId) : api.getOnsitePack(country);
    load
      .then((res) => {
        if (cancelled) return;
        setPack(res);
        setActiveType((prev) => prev ?? res.incident_types[0]?.type_id ?? null);
      })
      .catch(() => {
        if (!cancelled) {
          setPack(null);
          setError("현지 대응 정보를 불러오지 못했어요. 잠시 뒤 다시 시도해 주세요.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tripId, country]);

  const docs = useMemo<OnsiteDocOut[]>(() => {
    if (!pack || activeType == null) return [];
    return pack.docs_by_type[String(activeType)] ?? [];
  }, [pack, activeType]);

  const localOnly = docs.filter((d) => d.acquire_location === LOCAL_ONLY);
  const others = docs.filter((d) => d.acquire_location !== LOCAL_ONLY);
  const activeTypeName =
    pack?.incident_types.find((t) => t.type_id === activeType)?.name ?? "필요서류";

  const daysLeft = useMemo(() => {
    if (!pack?.end_date) return null;
    const end = new Date(`${pack.end_date}T00:00:00`);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Math.round((end.getTime() - today.getTime()) / 86_400_000);
  }, [pack]);

  return (
    <div className="page">
      <TopBar title="해외 서류 챙기기" />
      <PageHero
        icon="airplane"
        eyebrow="ON SITE"
        title={"귀국하면 못 받는\n서류부터 챙겨요"}
        subtitle="약관이 요구하는 형식을 현지어로 보여드려요. 병원·경찰서 창구에 이 화면을 그대로 보여주세요."
      />

      {offline && pack && (
        <div className="onsite-offline-badge">
          오프라인 — 마지막으로 받아둔 내용을 보고 있어요
        </div>
      )}

      {!tripId && (
        <div className="card">
          <p className="section-label" style={{ marginBottom: 8 }}>어느 나라에 계신가요?</p>
          <PickerField
            value={country}
            options={COUNTRIES.map((c) => ({ value: c, label: c }))}
            placeholder="나라 선택"
            modalTitle="나라 선택"
            onChange={setCountry}
          />
          <p className="muted" style={{ fontSize: "0.76rem", marginTop: 8 }}>
            여행을 등록하면 남은 일정과 등록한 보험사 기준으로 더 정확하게 안내해 드려요.
          </p>
        </div>
      )}

      {loading && <LoadingState label="현지 대응 정보를 준비하고 있어요..." />}
      {!loading && error && <div className="error-box">{error}</div>}

      {!loading && !pack && !error && !tripId && !country && (
        <div className="empty-state">
          <Icon3D src="suitcase" size={56} />
          <p className="muted">나라를 고르면 그 나라 말로 된 서류 요청 카드를 만들어 드려요.</p>
        </div>
      )}

      {!loading && pack && (
        <>
          {/* --- 1단: 남은 일정 + 현지only 진행률 --- */}
          <div className="card onsite-summary">
            <div className="onsite-summary__row">
              <div>
                <span className="section-label">지금 계신 곳</span>
                <strong className="onsite-summary__country">{pack.country ?? "-"}</strong>
              </div>
              {daysLeft != null && (
                <div className="onsite-dday">
                  <span className="onsite-dday__num">
                    {daysLeft > 0 ? `D-${daysLeft}` : daysLeft === 0 ? "D-DAY" : "귀국함"}
                  </span>
                  <span className="onsite-dday__label">귀국까지</span>
                </div>
              )}
            </div>

            {pack.progress_total != null ? (
              <div className="onsite-progress">
                <div className="onsite-progress__bar">
                  <div
                    className="onsite-progress__fill"
                    style={{
                      width: `${Math.round(((pack.progress_secured ?? 0) / pack.progress_total) * 100)}%`,
                    }}
                  />
                </div>
                <span className="onsite-progress__text">
                  현지에서만 받을 수 있는 서류 {pack.progress_total}건 중{" "}
                  <strong>{pack.progress_secured}건</strong> 확보
                </span>
              </div>
            ) : (
              <p className="muted" style={{ fontSize: "0.78rem", margin: "8px 0 0" }}>
                아직 접수한 사고가 없어요. 아래는 이 여행에서 사고가 났을 때
                <b> 현지에서만 받을 수 있는 서류</b>예요.
              </p>
            )}

            <p className="muted" style={{ fontSize: "0.74rem", marginTop: 10 }}>
              기준 약관: {pack.insurer_names.join(" · ")}
            </p>
          </div>

          {/* --- 사고유형 고르기 --- */}
          <div className="card">
            <p className="section-label" style={{ marginBottom: 8 }}>무슨 일이 있었나요?</p>
            <div className="calc-chips">
              {pack.incident_types.map((t) => (
                <button
                  key={t.type_id}
                  type="button"
                  className={`premium-chip${activeType === t.type_id ? " premium-chip--on" : ""}`}
                  onClick={() => setActiveType(t.type_id)}
                >
                  {t.name}
                </button>
              ))}
            </div>
          </div>

          {/* --- 2단: 현지어 서류 요청 카드 --- */}
          {docs.length === 0 ? (
            <div className="empty-state">
              <Icon3D src="file-text" size={56} />
              <p className="muted">이 사고유형에 연결된 필요서류가 아직 없어요.</p>
            </div>
          ) : (
            <>
              <div className="onsite-intro card">
                <span className="onsite-intro__label">
                  창구에 이 문장을 보여주세요 · {pack.lang_name_ko}
                </span>
                {pack.intro_local && <p className="onsite-intro__local">{pack.intro_local}</p>}
                <p className="onsite-intro__ko">{pack.intro_ko}</p>
              </div>

              {localOnly.length > 0 && (
                <>
                  <p className="section-label onsite-group-label">
                    귀국하면 못 받아요 · {localOnly.length}건
                  </p>
                  {localOnly.map((doc, i) => (
                    <DocCard key={doc.required_doc_std_id} doc={doc} index={i} urgent />
                  ))}
                </>
              )}

              {others.length > 0 && (
                <>
                  <p className="section-label onsite-group-label">
                    귀국 후에도 준비할 수 있어요 · {others.length}건
                  </p>
                  {others.map((doc, i) => (
                    <DocCard key={doc.required_doc_std_id} doc={doc} index={i} />
                  ))}
                </>
              )}

              {/* 창구 앞은 데이터가 잘 안 터지고, 폰을 직원에게 넘겨줘야 할 때도 있다 —
                  앱을 열어야만 볼 수 있으면 정작 필요한 순간에 못 쓴다. */}
              <OnsiteExport pack={pack} docs={docs} typeName={activeTypeName} />
            </>
          )}

          {/* --- 3단: 오프라인 --- */}
          <div className="card onsite-offline">
            <Icon3D src="wifi" size={28} />
            <div>
              <strong>비행기모드에서도 열려요</strong>
              <p className="muted" style={{ fontSize: "0.76rem", margin: "4px 0 0" }}>
                이 화면을 한 번 열어두면 데이터가 없는 곳에서도 그대로 볼 수 있어요.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/** 서류 한 장. 현지어와 한국어를 항상 함께 보여주고, 근거 조항은 한국어 원문 그대로 인용한다. */
function DocCard({ doc, index, urgent }: { doc: OnsiteDocOut; index: number; urgent?: boolean }) {
  return (
    <motion.div
      className={`card onsite-doc${urgent ? " onsite-doc--urgent" : ""}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 6) * 0.03 }}
    >
      <div className="onsite-doc__head">
        <div className="onsite-doc__names">
          {doc.doc_name_local && <strong className="onsite-doc__local">{doc.doc_name_local}</strong>}
          <span className="onsite-doc__ko">{doc.doc_name_ko}</span>
        </div>
        {doc.status && doc.status !== "미확인" && (
          <span className="onsite-doc__status">{doc.status}</span>
        )}
      </div>

      {doc.note && <p className="onsite-doc__note">{doc.note}</p>}

      {doc.requirements.length > 0 && (
        <div className="onsite-req-list">
          <span className="onsite-req-list__label">약관이 요구하는 것</span>
          {doc.requirements.map((req, i) => (
            <div className="onsite-req" key={`${req.clause_id}-${i}`}>
              {req.label_local && <p className="onsite-req__local">{req.label_local}</p>}
              <p className="onsite-req__ko">{req.label_ko}</p>
              {req.clause_quote && (
                <blockquote className="onsite-req__quote">
                  <span className="onsite-req__source">
                    {req.insurer_name} {req.clause_article_no}
                  </span>
                  {req.clause_quote}
                </blockquote>
              )}
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
