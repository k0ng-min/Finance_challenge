// 배포 환경에서는 Vite 빌드 시점에 VITE_API_BASE 환경변수로 실제 백엔드 주소를 주입한다
// (Render 등 호스팅 대시보드에서 설정). 로컬 개발 중에는 값이 없으므로 localhost로 fallback.
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const LS_TOKEN = "travel_ai_token";

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
  if (!res.ok) throw new ApiError(res.status, await res.text());
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
  /** 나이·성별을 함께 넘긴 경우의 보험다모아 공시 원문 값. 여행일수로 환산하지 않는다. */
  published_premium: number | null;
  premium_period_days: number | null;
  premium_basis: string | null;
  premium_source: string | null;
  premium_source_url: string | null;
  premium_collected_at: string | null;
  premium_note: string | null;
}

export interface InsurerRankingOut {
  tier_code: string;
  ranking: InsurerRankOut[];
}

export interface InsurerPremiumOut {
  insurer_code: string;
  insurer_name: string;
  product_name: string | null;
  published_premium: number;
  age_range: string | null;
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
  /** 해당 나이가 가입연령 밖이라 비교공시에 나오지 않는 보험사 */
  unavailable_insurers: string[];
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

export const api = {
  createUser: (nickname: string) =>
    request<UserOut>("/users", { method: "POST", body: JSON.stringify({ nickname }) }),

  createTrip: (payload: object) =>
    request<RecommendationOut>("/trips", { method: "POST", body: JSON.stringify(payload) }),

  getTrip: (tripId: number) => request<RecommendationOut>(`/trips/${tripId}`),

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

  getPremiumComparison: (age: number, sex: string, order: "asc" | "desc") =>
    request<PremiumComparisonOut>(`/insurers/premiums?age=${age}&sex=${sex}&order=${order}`),

  getInsurerCoverages: (insurerCode: string) =>
    request<InsurerCoverageOut[]>(`/insurers/${insurerCode}/coverages`),

  getInsurerIncidentCoverages: (insurerCode: string, typeId: number) =>
    request<InsurerIncidentCoverageOut[]>(`/insurers/${insurerCode}/incident-types/${typeId}/coverages`),

  getInsurerRanking: (
    tier: string,
    tripContext?: {
      destination?: string;
      risk_level?: string;
      trip_days?: number;
      activities?: string[];
      coverage_priority?: string[];
    },
    profile?: { age?: number | null; sex?: string | null }
  ) => {
    const params = new URLSearchParams({ tier });
    if (profile?.age != null) params.set("age", String(profile.age));
    if (profile?.sex) params.set("sex", profile.sex);
    if (tripContext?.destination) params.set("destination", tripContext.destination);
    if (tripContext?.risk_level) params.set("risk_level", tripContext.risk_level);
    if (tripContext?.trip_days) params.set("trip_days", String(tripContext.trip_days));
    if (tripContext?.activities?.length) params.set("activities", tripContext.activities.join(","));
    if (tripContext?.coverage_priority?.length) params.set("coverage_priority", tripContext.coverage_priority.join(","));
    return request<InsurerRankingOut>(`/insurers/ranking?${params.toString()}`);
  },

  getClause: (clauseId: number) => request<ClauseOut>(`/clauses/${clauseId}`),

  getClauseSpans: (clauseId: number) =>
    request<HighlightSpanOut[] | null>(`/clauses/${clauseId}/spans`),

  getClauseRelevance: (clauseId: number, incidentId: number) =>
    request<ClauseRelevanceOut>(`/clauses/${clauseId}/relevance?incident_id=${incidentId}`),

  getClausePlainText: (clauseId: number, incidentId?: number | null) =>
    request<{ plain_text: string | null; supported: boolean }>(
      `/clauses/${clauseId}/plain${incidentId ? `?incident_id=${incidentId}` : ""}`
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

  // 이메일/비밀번호 회원가입·로그인은 지원하지 않는다 — 카카오·구글만 쓴다.
  submitConsent: (consent: { agreeTerms: boolean; agreePrivacy: boolean; agreeMarketing: boolean }) =>
    request<{ status: string }>("/auth/consent", {
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
