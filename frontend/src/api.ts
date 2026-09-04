// 배포 환경에서는 Vite 빌드 시점에 VITE_API_BASE 환경변수로 실제 백엔드 주소를 주입한다
// (Render 등 호스팅 대시보드에서 설정). 로컬 개발 중에는 값이 없으므로 localhost로 fallback.
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const LS_TOKEN = "travel_ai_token";

/** 서버가 세션을 끊었을 때 앱 전체에 알리는 신호. AppContext가 듣고 게스트로 되돌린다. */
export const SESSION_EXPIRED_EVENT = "travel-ai:session-expired";

/**
 * 서버가 토큰을 거절했을 때(401) 브라우저에 남은 죽은 토큰을 치운다.
 *
 * 서버는 세션 유효기간이 지났거나, 로그인 계정이 30분 넘게 아무 요청도 보내지 않으면
 * 세션을 끊는다. 그때 브라우저가 죽은 토큰을 그대로 들고 있으면 화면은 로그인 상태로
 * 보이는데 누르는 것마다 실패하는, 사용자가 원인을 짐작할 수 없는 상태가 된다.
 *
 * 로그인 요청 자체의 401은 건드리지 않는다. 비밀번호를 한 번 틀렸을 뿐인데 그 브라우저에
 * 있던 게스트 세션까지 날아가면, 로그인 전에 쌓아둔 여행·사고 기록을 잃는다.
 */
function handleUnauthorized(path: string, sentToken: boolean) {
  if (!sentToken || path.startsWith("/auth/login")) return;
  localStorage.removeItem(LS_TOKEN);
  localStorage.removeItem("travel_ai_nickname");
  localStorage.removeItem("travel_ai_email");
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem(LS_TOKEN);
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });
  if (!res.ok) {
    if (res.status === 401) handleUnauthorized(path, Boolean(token));
    const body = await res.text();
    throw new ApiError(res.status, body);
  }
  return res.json();
}

/** 파일 업로드용. JSON 헤더를 붙이지 않는 것만 request와 다르다. */
async function requestForm<T>(path: string, body: FormData): Promise<T> {
  const token = localStorage.getItem(LS_TOKEN);
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body,
  });
  if (!res.ok) {
    if (res.status === 401) handleUnauthorized(path, Boolean(token));
    throw new ApiError(res.status, await res.text());
  }
  return res.json();
}

export interface DocCheckOut {
  code: string;
  label: string;
  found: boolean;
  quote: string | null;
  /** 채워져 있으면 약관 근거가 있는 요건이다. */
  clause_article_no: string | null;
  clause_text: string | null;
}

export interface DocVerifyOut {
  required_doc_std_id: number;
  doc_name: string;
  readable: boolean;
  detected_doc_type: string | null;
  language: string | null;
  translation: string | null;
  message: string;
  applied_status: string | null;
  grounded: DocCheckOut[];
  practical: DocCheckOut[];
  checklist: ChecklistOut;
}

/**
 * 서버가 돌려준 에러. 화면에는 절대 이 객체의 raw 본문을 그대로 쓰지 말고
 * userMessage(사람이 읽는 한 줄)만 보여준다 — 예전에는 페이지마다 String(err)를 그대로
 * 렌더링해서 `Error: API 404: {"detail":"..."}` 가 사용자에게 노출됐다.
 */
export class ApiError extends Error {
  readonly status: number;
  /** 서버가 준 detail 문구(있으면). 개발자용이며 그대로 노출해도 되는 말인지는 별개다. */
  readonly detail: string | null;

  constructor(status: number, body: string) {
    super(`API ${status}: ${body}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = parseDetail(body);
  }
}

function parseDetail(body: string): string | null {
  try {
    const parsed = JSON.parse(body);
    const detail = parsed?.detail;
    if (typeof detail === "string") return detail;
    // FastAPI 검증 오류는 detail이 배열이라 사람이 읽을 문장이 아니다 — 버린다.
    return null;
  } catch {
    return null;
  }
}

const STATUS_MESSAGES: Record<number, string> = {
  401: "로그인이 풀렸어요. 다시 로그인해 주세요.",
  403: "이 정보를 볼 권한이 없어요.",
  404: "찾는 정보가 없어요. 없어졌거나 아직 만들어지지 않았을 수 있어요.",
  409: "이미 처리된 요청이에요.",
  413: "파일이 너무 커요. 조금 더 작은 파일로 다시 시도해 주세요.",
  422: "입력한 내용을 다시 확인해 주세요.",
  429: "요청이 너무 잦아요. 잠시 뒤에 다시 시도해 주세요.",
};

/**
 * 어떤 예외든 화면에 그대로 띄울 수 있는 한 문장으로 바꾼다.
 *
 * 서버 detail은 우리가 직접 쓴 한국어 안내문일 때만 쓴다. 문장부호 없이 영문·중괄호가
 * 섞인 값(스택트레이스, 검증 오류 등)은 사용자에게 의미가 없으므로 상태코드 기반 문구로
 * 대체한다.
 */
export function userMessage(err: unknown, fallback = "잠시 문제가 생겼어요. 다시 시도해 주세요."): string {
  if (err instanceof ApiError) {
    if (err.detail && isHumanReadable(err.detail)) return err.detail;
    return STATUS_MESSAGES[err.status] ?? (err.status >= 500
      ? "서버가 잠깐 쉬고 있어요. 잠시 뒤에 다시 시도해 주세요."
      : fallback);
  }
  // fetch 자체가 실패한 경우(네트워크 끊김, 서버 미기동 등)
  if (err instanceof TypeError) return "서버에 연결하지 못했어요. 인터넷 연결을 확인해 주세요.";
  return fallback;
}

/** 한글이 들어 있고 JSON 조각처럼 보이지 않으면 우리가 쓴 안내문으로 본다. */
function isHumanReadable(text: string): boolean {
  if (text.length > 120) return false;
  if (/[{}[\]<>]/.test(text)) return false;
  return /[가-힣]/.test(text);
}

export interface HighlightSpanOut {
  text: string;
  color: string;
}

export interface RelevanceSegment {
  text: string;
  highlighted: boolean;
}

export interface ClauseRelevanceOut {
  segments: RelevanceSegment[];
  relevant_chars: number;
  supported: boolean;
}

export interface ClauseTermOut {
  term_type: string;
  value_num: number | null;
  unit: string | null;
  basis: string | null;
  condition_text: string | null;
  raw_text: string;
}

export interface ClauseOut {
  clause_id: number;
  article_no: string;
  text: string;
  page_ref: string | null;
  default_color: string;
  highlight_color: string;
  highlight_spans?: HighlightSpanOut[] | null;
  terms?: ClauseTermOut[];
}

export interface FindingOut {
  finding_id: number;
  finding_type: string;
  status: string;
  target_ref: string | null;
  insurer_code: string | null;
  insurer_name: string | null;
  description: string;
  confidence: string | null;
  coverage_amount: string | null;
  /** 등록한 등급 기준 실제 가입금액("5,000만원 (실속형 기준)"). 약관 한도와 다른 값이다. */
  plan_amount: string | null;
  clauses: ClauseOut[];
}

export interface RecommendationOut {
  analysis_run_id: number;
  trip_id: number;
  risk_profile: Record<string, unknown>;
  findings: FindingOut[];
}

export interface UserOut {
  user_id: number;
  nickname: string;
  /** 게스트도 이 토큰으로 본인을 증명한다(익명 접근은 서버에서 막혀 있다). */
  token: string;
}

export interface UserCoverageOut {
  user_coverage_id: number;
  raw_name: string;
  subscribed_amount: string | null;
  matched_std_code: string | null;
  matched_std_name: string | null;
  match_confidence: number;
}

export interface InsurerCoverageOut {
  coverage_id: number;
  std_code: string | null;
  std_name: string | null;
  raw_name: string;
  definition: string | null;
  limit_amount: string | null;
  deductible: string | null;
}

export interface UserPolicyOut {
  user_policy_id: number;
  insurer_name_raw: string;
  product_name_raw: string | null;
  plan_name: string | null;
  subscriber_age: number | null;
  period_start: string;
  period_end: string;
  matched_insurer_code: string | null;
  matched_insurer_name: string | null;
  matched_product_name: string | null;
  coverages: UserCoverageOut[];
}

export interface PendingQuestionOut {
  question_id: number;
  question_text: string;
  target_field: string;
  impact_weight: number;
  /** "yesno"면 예/아니오 버튼, "text"면 한 줄 입력칸으로 그린다. */
  answer_type: string;
  /** "L1"(대분류 확인) | "L2"(세부유형 확인). 옛 공용 질문은 null. */
  stage: string | null;
}

export interface ValidationResultOut {
  rule_code: string;
  rule_name: string;
  severity: string;
  passed: boolean;
  detail: string;
}

export interface IncidentAnalysisOut {
  incident_id: number;
  analysis_run_id: number;
  structured: Record<string, { value: unknown; confidence: number; source_span: string | null }>;
  findings: FindingOut[];
  pending_questions: PendingQuestionOut[];
  validation_results: ValidationResultOut[];
  linked_insurer_code: string | null;
  linked_insurer_name: string | null;
  linked_product_name: string | null;
  trip_id: number | null;
  trip_destination: string | null;
  trip_start_date: string | null;
  trip_end_date: string | null;
  incident_country: string | null;
}

export interface ChecklistItemOut {
  required_doc_std_id: number;
  doc_code: string;
  doc_name: string;
  acquire_location: string;
  is_mandatory: boolean;
  coverage_target_ref: string;
  insurer_name: string;
  status: string;
  memo: string | null;
  clause: ClauseOut | null;
}

export interface ChecklistOut {
  incident_id: number;
  items: ChecklistItemOut[];
  validation_results: ValidationResultOut[];
  trip_id: number | null;
  trip_destination: string | null;
  trip_start_date: string | null;
  trip_end_date: string | null;
  incident_country: string | null;
}

export interface IncidentTypeOut {
  type_id: number;
  l1_code: string;
  name: string;
}

export interface InsurerIncidentCoverageOut {
  coverage_id: number;
  coverage_name: string;
  relevance: string;
  limit_amount: string | null;
  clauses: ClauseOut[];
}

export interface StandardClauseOut {
  standard_clause_id: number;
  article_no: string;
  title: string;
  text: string;
  amended_at: string | null;
}

export interface StandardClauseComparisonOut {
  standard_clause_id: number;
  article_no: string;
  title: string;
  standard_text: string;
  anchor_phrase_standard: string;
  relation: "SAME" | "BROADER" | "NARROWER" | "MISSING_IN_INSURER";
  insurer_clause_id: number | null;
  insurer_article_no: string | null;
  insurer_text: string | null;
  anchor_phrase_insurer: string | null;
  note: string | null;
}

export interface InsurerStandardComparisonOut {
  insurer_code: string;
  insurer_name: string;
  standard_name: string;
  source_url: string;
  amended_at: string | null;
  items: StandardClauseComparisonOut[];
}

export interface NonpaymentRateOut {
  insurer_code: string | null;
  company_name: string;
  claim_count: number;
  unpaid_count: number;
  unpaid_rate: number;
  post_claim_cancel_rate: number | null;
}

export interface NonpaymentRatesOut {
  source: string;
  source_url: string;
  period: string;
  scope_note: string;
  collected_at: string | null;
  items: NonpaymentRateOut[];
  industry_average: NonpaymentRateOut | null;
}

export interface FlightDelayStatOut {
  kind: string;
  direction: string;
  delayed_flights: number;
  avg_delay_minutes: number | null;
  passengers_affected: number | null;
}

export interface ClauseIncidentLinkOut {
  type_name: string;
  relevance: string;
}

export interface ClauseSearchResultOut {
  clause: ClauseOut;
  incident_links: ClauseIncidentLinkOut[];
}

export interface FlightDelayStatsOut {
  source: string;
  source_url: string;
  coverage_period: string;
  scope_note: string;
  collected_at: string | null;
  overall: FlightDelayStatOut[];
}

export interface InsurerTierOut {
  tier_code: string;
  label: string;
  description: string;
}

export interface RankingEvidenceOut {
  kind: string;
  source_id: number;
  coverage_name: string;
  description: string;
  page_ref: string | null;
}

export interface RankingDimensionOut {
  code: string;
  label: string;
  /** 보험사 사이 상대 단계 1~5. 근거가 부족하면 0. */
  level: number;
  status: string;
  summary: string;
  evidence_count: number;
  evidence: RankingEvidenceOut[];
  comparison_state: "AVAILABLE" | "UNKNOWN" | "NOT_APPLICABLE";
  available: boolean;
  known_count: number;
  total_count: number;
  completeness_rate: number | null;
}

export interface RankingAxisOut {
  /** amount | clause | price | overlap | activity */
  code: string;
  label: string;
  /** 0~1 */
  score: number;
  /** 자료 없는 축을 빼고 재정규화한 뒤 실제로 쓰인 비중 */
  weight: number;
  /** score × weight × 100 — 이번 총점에 이 축이 넣은 몫 */
  contribution: number;
  /** false면 자료가 없어 이 축을 빼고 나머지로 100%를 다시 맞췄다 */
  available: boolean;
  detail: string;
  comparison_state: "AVAILABLE" | "UNKNOWN" | "NOT_APPLICABLE";
}

export interface InsurerRankOut {
  rank: number;
  insurer_code: string;
  insurer_name: string;
  comparison_basis: string;
  dimensions: RankingDimensionOut[];
  reasons: string[];
  tags: string[];
  official_url: string | null;
  /** 나이·성별을 함께 넘긴 경우, 보험사 다이렉트 사이트에서 직접 조회한 실제 값. 여행일수로 환산하지 않는다. */
  published_premium: number | null;
  /** published_premium이 어느 등급 가격인지(plan_tier로 고른 등급). 상세 화면에 들어갈 때
   * 이 등급을 그대로 이어서 보여준다. */
  plan_name: string | null;
  premium_period_days: number | null;
  premium_basis: string | null;
  premium_source: string | null;
  premium_source_url: string | null;
  premium_collected_at: string | null;
  premium_value_origin: PremiumValueOrigin | null;
  premium_source_value: number | null;
  premium_source_period_days: number | null;
  premium_transformation: string | null;
  premium_transformation_reason: string | null;
  premium_source_reference: string | null;
  premium_note: string | null;
  /** 가중치 점수 모델의 총점(0~100). plan_tier를 함께 넘겼을 때만 채워진다. */
  total_score: number | null;
  /** 총점을 만든 다섯 축의 점수·비중·기여도. */
  axes: RankingAxisOut[];
  /** 등급별 담보 가입금액표를 볼 수 있는 보험사면 그 담보 항목 수(순위 점수에는 섞이지 않는다). */
  plan_coverage_item_count: number | null;
}

export interface InsurerRankingOut {
  tier_code: string;
  ranking: InsurerRankOut[];
  /** 그 등급 상품이 없어 비교에서 빠진 보험사가 있으면 그 사실을 알리는 한 줄. */
  excluded_note: string | null;
}

export type PremiumValueOrigin = "DIRECT_QUOTE" | "DERIVED" | "IMPUTED" | "UNKNOWN";

export interface PremiumProvenanceOut {
  value_origin: PremiumValueOrigin;
  source_value: number | null;
  source_period_days: number | null;
  transformation: string | null;
  transformation_reason: string | null;
  source_reference: string | null;
}

export interface InsurerPremiumOut extends PremiumProvenanceOut {
  insurer_code: string;
  insurer_name: string;
  product_name: string | null;
  published_premium: number;
  premium_period_days: number;
  age_range: string | null;
  /** 이 보험사의 산출 전제와 조회일 — 보험사마다 다르다(전제·조회일이 갈린다). */
  basis: string | null;
  source: string | null;
  source_url: string | null;
  collected_at: string | null;
}

export interface PremiumComparisonOut {
  age: number;
  sex: string;
  basis: string | null;
  source: string | null;
  source_url: string | null;
  collected_at: string | null;
  premium_period_days: number;
  items: InsurerPremiumOut[];
  /** 가격을 추적 중인데 이 나이만 가입연령 범위 밖인 보험사(이름) */
  unavailable_insurers: string[];
  /** 나이와 무관하게 가격을 아직 하나도 못 구한 보험사(코드). 현재 비교 대상은 전부
   *  가격이 있어 비어 있지만, 보험사를 새로 추가하면 그 사이 다시 채워진다. */
  no_data_insurer_codes: string[];
}

export interface InsurerPlanOut extends PremiumProvenanceOut {
  plan_name: string;
  premium: number;
  premium_period_days: number;
  is_standard_tier: boolean;
  collected_at: string | null;
}

export interface InsurerPlansOut {
  insurer_code: string;
  insurer_name: string;
  premium_period_days: number;
  plans: InsurerPlanOut[];
  /** 이 나이·성별(또는 아예) 가격 자료가 없으면 true — 등급 이름만 있고 가격은 비어 있다. */
  price_unavailable: boolean;
}

export interface InsurerPlanCoverageRowOut {
  plan_name: string;
  coverage_label: string;
  amount_text: string;
  unit: string;
  sort_order: number;
}

export interface InsurerPlanCoverageOut {
  insurer_code: string;
  insurer_name: string;
  plan_names: string[];
  rows: InsurerPlanCoverageRowOut[];
  source: string | null;
  source_note: string | null;
  collected_at: string | null;
}

export interface ComparisonMetricValueOut {
  insurer_code: string;
  value_text: string;
}

export interface ComparisonMetricOut {
  metric_label: string;
  unit: string;
  values: ComparisonMetricValueOut[];
}

export interface ComparisonCategoryOut {
  category: string;
  metrics: ComparisonMetricOut[];
}

/** 전 보험사를 같은 담보 항목 기준으로 나란히 비교한 표(보장비교 종합), 등급 하나 기준. */
export interface InsurerComparisonOut {
  tier_rank: number;
  tier_label: string;
  categories: ComparisonCategoryOut[];
  source: string | null;
  source_note: string | null;
  collected_at: string | null;
}

/** 로그인 계정이 보험료 비교에서 담아 둔 보험사 목록("비교함"). 게스트는 저장하지 않는다. */
export interface PremiumWatchlistOut {
  insurer_codes: string[];
}

export interface AuthUserOut {
  user_id: number;
  nickname: string;
  email: string | null;
  auth_provider: string;
  token: string;
  age: number | null;
  sex: string | null;
  is_new_user: boolean;
  /** 닉네임·나이·필수동의까지 마친 계정인지. false면 어느 화면에 있든 가입 마무리 화면으로 되돌린다. */
  signup_completed: boolean;
  /** 이메일+비밀번호로도 로그인할 수 있게 비밀번호를 정해 뒀는지. */
  has_password: boolean;
}

export interface ProviderStatusOut {
  kakao_enabled: boolean;
  google_enabled: boolean;
  kakao_client_id: string;
  google_client_id: string;
  kakao_redirect_uri: string;
  google_redirect_uri: string;
}

export interface TripDetailOut {
  trip_id: number;
  destination: string | null;
  start_date: string | null;
  end_date: string | null;
  purpose: string | null;
  companion_type: string | null;
  user_policy_id: number | null;
  insurer_name: string | null;
}

export interface TripSummaryOut {
  trip_id: number;
  destination: string | null;
  start_date: string | null;
  end_date: string | null;
  risk_level: string | null;
  /** 이 여행에 등록해 둔 보험. 아직 보험을 붙이지 않았으면 null. */
  user_policy_id: number | null;
}

export interface IncidentSummaryOut {
  incident_id: number;
  country: string | null;
  occurred_at: string | null;
  diagnosis: string | null;
  cause: string | null;
  user_policy_id: number | null;
  linked_insurer_code: string | null;
  linked_insurer_name: string | null;
}

export type ExternalPolicyKind =
  | "MEDICAL_INDEMNITY" | "ACCIDENT" | "DAILY_LIABILITY" | "DRIVER" | "OTHER";

export interface ExternalPolicyOut {
  external_policy_id: number;
  source: string;
  kind: ExternalPolicyKind;
  insurer_name_raw: string | null;
  product_name_raw: string | null;
  enrolled_ym: string | null;
  indemnity_gen: number | null;
  coverages: { external_coverage_id: number; raw_name: string | null; subscribed_amount: string | null; amount_source: string }[];
}

export interface ProviderOut {
  name: string;
  requires_login: boolean;
}

export interface OverlapFindingOut {
  coverage_std_code: string;
  coverage_std_name: string;
  external_kind: string;
  scope: string;
  relation: "NO_OVERLAP" | "DUPLICATE_PRORATA" | "DUPLICATE_FIXED" | "PARTIAL" | "UNKNOWN";
  note: string | null;
  clause_id: number | null;
  clause_article_no: string | null;
  clause_quote: string | null;
}

export interface OverlapReportOut {
  duplicates: OverlapFindingOut[];
  gaps: OverlapFindingOut[];
  fixed_ok: OverlapFindingOut[];
  unknown: OverlapFindingOut[];
}

/**
 * 외교부 여행경보. 국가가 아니라 **지역** 단위라 두 가지를 나눠 받는다.
 *
 * - `baseline` 그 나라 일반 지역의 단계. 국지적 경보만 있는 나라(일본 등)는 null이다.
 * - `regions`  지역별 경보. 3단계 이상이면 "이 지역에 가시나요?"를 묻는다.
 *
 * 일본의 3단계는 후쿠시마 원전 30km다. 이걸 국가 전체 경보로 표시하면 도쿄 여행자에게
 * 출국권고가 뜬다.
 */
export interface TravelAlertRow {
  alert_id: number | null;
  level: number;
  label: string;
  region_type: string | null;
  note: string | null;
  issued_on: string | null;
}

export interface TravelAlertOut {
  country_name: string;
  baseline: TravelAlertRow | null;
  baseline_basis: string;
  regions: TravelAlertRow[];
  source: string | null;
  source_url: string | null;
  /** 사용자가 "여기 간다"고 체크한 지역. 여행 생성 응답에만 실린다. */
  visiting_regions?: TravelAlertRow[];
}

// --- 현지 대응 팩(「현지에서」) ---------------------------------------------
// 한 번의 요청에 사고유형 8개분이 전부 담긴다. 오프라인 캐시에 실리는 단위가 요청
// 하나여야 비행기모드에서 화면이 온전히 뜬다.

export interface OnsiteRequirementOut {
  /** 한국어 원문. 현지어만 단독으로 나가는 일이 없도록 서버가 항상 채운다. */
  label_ko: string;
  /** 번역을 못 구하면 null — 화면은 그 자리에 한국어만 보여준다. */
  label_local: string | null;
  clause_id: number | null;
  clause_article_no: string | null;
  /** 조항 원문의 부분 문자열. 근거는 번역하지 않는다. */
  clause_quote: string | null;
  insurer_name: string | null;
}

export interface OnsiteDocOut {
  required_doc_std_id: number;
  doc_code: string;
  doc_name_ko: string;
  doc_name_local: string | null;
  /** 현지only | 귀국가능 | 공통 */
  acquire_location: string | null;
  note: string | null;
  /** 연결된 사고가 있을 때만 채워진다. */
  status: string | null;
  requirements: OnsiteRequirementOut[];
}

export interface OnsiteIncidentTypeOut {
  type_id: number;
  l1_code: string;
  name: string;
}

export interface OnsitePackOut {
  country: string | null;
  lang_code: string;
  lang_name_ko: string;
  intro_ko: string;
  intro_local: string | null;
  trip_id: number | null;
  start_date: string | null;
  end_date: string | null;
  insurer_names: string[];
  incident_types: OnsiteIncidentTypeOut[];
  docs_by_type: Record<string, OnsiteDocOut[]>;
  /** 연결된 사고가 없으면 null — 0/N으로 지어내지 않는다. */
  progress_total: number | null;
  progress_secured: number | null;
  generated_at: string;
}

// --- 사고 시뮬레이션 --------------------------------------------------------

export interface SimulationResultOut {
  insurer_name: string;
  /** 직접 | 조건부 | 면책 | 확인불가 */
  verdict: string;
  coverage_name: string | null;
  clause_article_no: string | null;
  clause_quote: string | null;
}

export interface SimulationSubTypeOut {
  type_id: number;
  name: string;
}

export interface SimulatedScenarioOut {
  code: string;
  title: string;
  narrative: string;
  l1_type_id: number;
  selected_type_id: number;
  incident_type_name: string;
  sub_types: SimulationSubTypeOut[];
  results: SimulationResultOut[];
}

export interface SimulationOut {
  trip_id: number;
  destination: string | null;
  start_date: string | null;
  end_date: string | null;
  scenarios: SimulatedScenarioOut[];
  disclaimer: string;
}

// --- 근거 검증 현황 ---------------------------------------------------------
export interface KbCheckOut {
  code: string;
  label: string;
  description: string;
  passed: number;
  total: number;
  /** 통과율(%) */
  rate: number;
}

export interface KbInsurerStatOut {
  insurer_code: string;
  insurer_name: string;
  clause_count: number;
  coverage_count: number;
  clause_term_count: number;
  incident_map_count: number;
  version_label: string | null;
  effective_date: string | null;
  /** 원본 PDF의 SHA-256 앞 12자리 */
  file_hash_prefix: string | null;
}

export interface KbStatsOut {
  insurer_count: number;
  clause_count: number;
  coverage_count: number;
  clause_term_count: number;
  incident_map_count: number;
  incident_type_l1_count: number;
  incident_type_l2_count: number;
  checks: KbCheckOut[];
  insurers: KbInsurerStatOut[];
}

/**
 * 서버가 깨어 있는지만 확인한다. 무료 호스팅(Render)은 15분간 요청이 없으면 잠들고,
 * 다음 요청이 들어오면 그 요청을 붙잡아 둔 채 컨테이너를 다시 띄운다 — 그동안 응답이
 * 30~60초까지 늦어진다. 부팅 때 이걸 먼저 한 번 두드려서, 앱이 "왜 아무 반응이 없지"가
 * 아니라 "지금 서버를 깨우는 중"이라고 정확히 말할 수 있게 한다.
 *
 * 다른 요청들과 달리 토큰도 JSON 헤더도 붙이지 않고, 응답 본문도 읽지 않는다 —
 * 돌아왔다는 사실 하나만 쓴다. timeoutMs가 지나면 요청을 끊는데, 끊어도 서버를 깨우는
 * 일 자체는 계속 진행되므로 다시 두드리면 된다.
 */
export async function pingHealth(timeoutMs = 20000): Promise<void> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: controller.signal });
    if (!res.ok) throw new ApiError(res.status, "health");
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  /** 약관 KB 규모와 근거 검증 통과율. 서버가 DB에서 직접 세어 내려준다. */
  getKbStats: () => request<KbStatsOut>("/insurers/kb-stats"),

  createUser: (nickname: string) =>
    request<UserOut>("/users", { method: "POST", body: JSON.stringify({ nickname }) }),

  createTrip: (payload: object) =>
    request<RecommendationOut>("/trips", { method: "POST", body: JSON.stringify(payload) }),

  getTrip: (tripId: number) => request<RecommendationOut>(`/trips/${tripId}`),

  /** 이 여행 기준 현지 대응 팩. 보험이 연결돼 있으면 그 보험사 요건만 담긴다. */
  getTripOnsitePack: (tripId: number) => request<OnsitePackOut>(`/trips/${tripId}/onsite`),

  /** 여행 없이 나라만으로 보는 현지 대응 팩(게스트 가능). */
  getOnsitePack: (country: string) =>
    request<OnsitePackOut>(`/onsite?country=${encodeURIComponent(country)}`),

  /**
   * 사고 시뮬레이션. selected는 {시나리오코드: L2 사고유형 id} —
   * 고르지 않은 시나리오는 L1 기준으로 계산된다.
   */
  getTripSimulation: (tripId: number, selected: Record<string, number> = {}) => {
    const params = Object.entries(selected)
      .map(([code, typeId]) => `select=${encodeURIComponent(`${code}:${typeId}`)}`)
      .join("&");
    return request<SimulationOut>(`/trips/${tripId}/simulation${params ? `?${params}` : ""}`);
  },

  /** 세분화 칩 하나를 눌렀을 때 그 시나리오 하나만 다시 계산한다 — 나머지
   * 시나리오는 화면에 이미 있는 결과를 그대로 둔다. */
  getTripSimulationScenario: (tripId: number, code: string, typeId: number | null) => {
    const q = typeId != null ? `?type_id=${typeId}` : "";
    return request<SimulatedScenarioOut>(
      `/trips/${tripId}/simulation/${encodeURIComponent(code)}${q}`,
    );
  },

  /** 목적지 여행경보. 자료에 없는 나라면 alert가 null이다(추측하지 않는다). */
  getTravelAlert: (country: string) =>
    request<{ alert: TravelAlertOut | null }>(`/trips/travel-alerts/${encodeURIComponent(country)}`),

  getTripDetail: (tripId: number) => request<TripDetailOut>(`/trips/${tripId}/detail`),

  updateTrip: (tripId: number, payload: object) =>
    request<TripDetailOut>(`/trips/${tripId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  listPolicies: (userId: number) => request<UserPolicyOut[]>(`/users/${userId}/policies`),

  registerPolicy: (userId: number, payload: object) =>
    request<UserPolicyOut>(`/users/${userId}/policies`, { method: "POST", body: JSON.stringify(payload) }),

  deletePolicy: (userId: number, policyId: number) =>
    request<{ status: string }>(`/users/${userId}/policies/${policyId}`, { method: "DELETE" }),

  createIncident: (payload: object) =>
    request<IncidentAnalysisOut>("/incidents", { method: "POST", body: JSON.stringify(payload) }),

  getIncident: (incidentId: number) => request<IncidentAnalysisOut>(`/incidents/${incidentId}`),

  answerQuestion: (incidentId: number, questionId: number, answerText: string) =>
    request<IncidentAnalysisOut>(`/incidents/${incidentId}/answers`, {
      method: "POST",
      body: JSON.stringify({ question_id: questionId, answer_text: answerText }),
    }),

  /** 한 페이지에 뜬 질문의 답을 한 번에 보낸다 — 답마다 따로 보내면 분석이 그 수만큼 돈다. */
  answerQuestionsBatch: (
    incidentId: number,
    answers: { question_id: number; answer_text: string }[],
    extraNote?: string,
  ) =>
    request<IncidentAnalysisOut>(`/incidents/${incidentId}/answers/batch`, {
      method: "POST",
      body: JSON.stringify({ answers, extra_note: extraNote || null }),
    }),

  getChecklist: (incidentId: number) => request<ChecklistOut>(`/incidents/${incidentId}/checklist`),

  /** 서류 사진을 올려 번역·요건 대조를 받는다. 사진은 서버에 저장되지 않는다. */
  verifyDocumentPhoto: (incidentId: number, docStdId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    // Content-Type을 직접 지정하면 boundary가 빠져 서버가 파싱하지 못한다 — 브라우저가 붙이게 둔다.
    return requestForm<DocVerifyOut>(`/incidents/${incidentId}/documents/${docStdId}/verify`, form);
  },

  getInsurerTiers: () => request<InsurerTierOut[]>("/insurers/ranking-tiers"),

  getIncidentTypes: () => request<IncidentTypeOut[]>("/incidents/types"),

  getPremiumComparison: (age: number, sex: string, order: "asc" | "desc", planTier?: number) => {
    const q = planTier != null ? `&plan_tier=${planTier}` : "";
    return request<PremiumComparisonOut>(`/insurers/premiums?age=${age}&sex=${sex}&order=${order}${q}`);
  },

  /** 한 보험사가 실제로 파는 등급(플랜) 전부와 가격. age·sex를 안 주면 가격 없이
   * 등급 이름만 온다(나이를 아직 모르는 단계에서도 등급은 먼저 보여줄 수 있다). */
  getInsurerPlans: (insurerCode: string, age?: number, sex?: "M" | "F") => {
    const q = age != null && sex ? `?age=${age}&sex=${sex}` : "";
    return request<InsurerPlansOut>(`/insurers/${insurerCode}/plans${q}`);
  },

  /** 한 보험사의 등급별 담보 가입금액표(나이·성별 무관). */
  getInsurerPlanCoverage: (insurerCode: string) =>
    request<InsurerPlanCoverageOut>(`/insurers/${insurerCode}/plan-coverage`),

  getInsurerCoverages: (insurerCode: string) =>
    request<InsurerCoverageOut[]>(`/insurers/${insurerCode}/coverages`),

  getInsurerIncidentCoverages: (insurerCode: string, typeId: number) =>
    request<InsurerIncidentCoverageOut[]>(`/insurers/${insurerCode}/incident-types/${typeId}/coverages`),

  getInsurerStandardComparison: (insurerCode: string) =>
    request<InsurerStandardComparisonOut>(`/insurers/${insurerCode}/standard-comparison`),

  getFlightDelayStats: () => request<FlightDelayStatsOut>(`/trips/flight-delay-stats`),

  getNonpaymentRates: () => request<NonpaymentRatesOut>(`/insurers/nonpayment-rates`),

  getInsurerRanking: (
    tier: string,
    tripContext?: {
      destination?: string;
      risk_level?: string;
      trip_days?: number;
      activities?: string[];
      coverage_priority?: string[];
      companion_type?: string | null;
      rental_car?: boolean;
    },
    profile?: { age?: number | null; sex?: string | null; user_id?: number | null },
    /** 0=실속, 1=표준(기본), 2=고급 — insurer_tiers.TIER_LABELS와 같은 순서. */
    planTier?: number
  ) => {
    const params = new URLSearchParams({ tier });
    if (profile?.age != null) params.set("age", String(profile.age));
    if (profile?.sex) params.set("sex", profile.sex);
    if (tripContext?.destination) params.set("destination", tripContext.destination);
    if (tripContext?.risk_level) params.set("risk_level", tripContext.risk_level);
    if (tripContext?.trip_days) params.set("trip_days", String(tripContext.trip_days));
    if (tripContext?.activities?.length) params.set("activities", tripContext.activities.join(","));
    if (tripContext?.coverage_priority?.length) params.set("coverage_priority", tripContext.coverage_priority.join(","));
    if (tripContext?.companion_type) params.set("companion_type", tripContext.companion_type);
    if (tripContext?.rental_car) params.set("rental_car", "true");
    // 등록해 둔 기존보험을 순위(겹침 축)에 반영하기 위해 넘긴다.
    if (profile?.user_id != null) params.set("user_id", String(profile.user_id));
    if (planTier != null) params.set("plan_tier", String(planTier));
    return request<InsurerRankingOut>(`/insurers/ranking?${params.toString()}`);
  },

  /** 전 보험사를 같은 담보 항목 기준으로 나란히 비교한 표(보장비교 종합), 등급 하나 기준. */
  getInsurerComparisonMetrics: (planTier: number) =>
    request<InsurerComparisonOut>(`/insurers/comparison-metrics?plan_tier=${planTier}`),

  /** 로그인 계정의 보험료 비교함. 게스트는 부를 필요가 없다(서버에 저장된 게 없다). */
  getPremiumWatchlist: (userId: number) =>
    request<PremiumWatchlistOut>(`/users/${userId}/premium-watchlist`),

  setPremiumWatchlist: (userId: number, insurerCodes: string[]) =>
    request<PremiumWatchlistOut>(`/users/${userId}/premium-watchlist`, {
      method: "PUT",
      body: JSON.stringify({ insurer_codes: insurerCodes }),
    }),

  getClause: (clauseId: number) => request<ClauseOut>(`/clauses/${clauseId}`),

  getClauseSpans: (clauseId: number) =>
    request<HighlightSpanOut[] | null>(`/clauses/${clauseId}/spans`),

  getClauseRelevance: (clauseId: number, incidentId: number) =>
    request<ClauseRelevanceOut>(`/clauses/${clauseId}/relevance?incident_id=${incidentId}`),

  getClausePlainText: (clauseId: number, incidentId?: number | null) =>
    request<{ plain_text: string | null; supported: boolean }>(
      `/clauses/${clauseId}/plain${incidentId ? `?incident_id=${incidentId}` : ""}`
    ),

  searchClauses: (insurerCode: string, keyword: string) =>
    request<ClauseSearchResultOut[]>(
      `/clauses/search?insurer_code=${encodeURIComponent(insurerCode)}&keyword=${encodeURIComponent(keyword)}`
    ),

  listTrips: (userId: number) => request<TripSummaryOut[]>(`/users/${userId}/trips`),

  listIncidents: (userId: number) => request<IncidentSummaryOut[]>(`/users/${userId}/incidents`),

  deleteTrip: (tripId: number) => request<{ status: string }>(`/trips/${tripId}`, { method: "DELETE" }),

  deleteIncident: (incidentId: number) => request<{ status: string }>(`/incidents/${incidentId}`, { method: "DELETE" }),

  submitEvidence: (incidentId: number, items: { required_doc_std_id: number; status: string; memo?: string }[]) =>
    request<ChecklistOut>(`/incidents/${incidentId}/evidence`, {
      method: "POST",
      body: JSON.stringify(items),
    }),

  // 회원가입은 카카오·구글로만 한다. 아래 loginWithEmail은 그렇게 가입한 계정이 계정
  // 화면에서 따로 정해 둔 비밀번호로 들어오는 통로다(비밀번호로 새 계정을 만들 수는 없다).
  loginWithEmail: (email: string, password: string) =>
    request<AuthUserOut>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  setPassword: (newPassword: string, currentPassword?: string | null) =>
    request<AuthUserOut>("/auth/password", {
      method: "POST",
      body: JSON.stringify({ new_password: newPassword, current_password: currentPassword ?? null }),
    }),

  /** 가입 마무리 전에 되돌아 나갈 때 — 아직 완료되지 않은 계정을 지운다. */
  cancelPendingSignup: () => request<{ status: string }>("/auth/signup-pending", { method: "DELETE" }),

  submitConsent: (consent: { agreeTerms: boolean; agreePrivacy: boolean; agreeMarketing: boolean }) =>
    request<AuthUserOut>("/auth/consent", {
      method: "POST",
      body: JSON.stringify({
        agree_terms: consent.agreeTerms, agree_privacy: consent.agreePrivacy, agree_marketing: consent.agreeMarketing,
      }),
    }),

  getMe: () => request<AuthUserOut>("/auth/me"),

  logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),

  getAuthProviders: () => request<ProviderStatusOut>("/auth/providers"),

  loginWithKakao: (code: string, userId: number | null, intent: "login" | "signup") =>
    request<AuthUserOut>("/auth/kakao", { method: "POST", body: JSON.stringify({ code, user_id: userId, intent }) }),

  loginWithGoogle: (code: string, userId: number | null, intent: "login" | "signup") =>
    request<AuthUserOut>("/auth/google", { method: "POST", body: JSON.stringify({ code, user_id: userId, intent }) }),

  updateNickname: (nickname: string) =>
    request<AuthUserOut>("/auth/nickname", { method: "PATCH", body: JSON.stringify({ nickname }) }),

  updateAge: (age: number) =>
    request<AuthUserOut>("/auth/age", { method: "PATCH", body: JSON.stringify({ age }) }),

  updateSex: (sex: string) =>
    request<AuthUserOut>("/auth/sex", { method: "PATCH", body: JSON.stringify({ sex }) }),

  deleteAccount: () => request<{ status: string }>("/auth/me", { method: "DELETE" }),

  listProviders: (userId: number) =>
    request<ProviderOut[]>(`/users/${userId}/external-policies/providers`),

  listExternalPolicies: (userId: number) =>
    request<ExternalPolicyOut[]>(`/users/${userId}/external-policies`),

  linkExternalPolicies: (
    userId: number,
    body: { provider: string; items: { kind: string; insurer_name_raw?: string | null; enrolled_ym?: string | null }[] },
  ) =>
    request<ExternalPolicyOut[]>(`/users/${userId}/external-policies/link`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteExternalPolicy: (userId: number, id: number) =>
    request<{ status: string }>(`/users/${userId}/external-policies/${id}`, { method: "DELETE" }),

  getCoverageOverlap: (userId: number, params: { tripId?: number; userPolicyId?: number }) => {
    const q = new URLSearchParams();
    if (params.tripId) q.set("trip_id", String(params.tripId));
    if (params.userPolicyId) q.set("user_policy_id", String(params.userPolicyId));
    return request<OverlapReportOut>(`/users/${userId}/coverage-overlap?${q.toString()}`);
  },
};
