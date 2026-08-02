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
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
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

export interface InsurerRankOut {
  rank: number;
  insurer_code: string;
  insurer_name: string;
  score: number;
  reasons: string[];
  tags: string[];
  official_url: string | null;
  /** 나이·성별을 함께 넘긴 경우에만 채워진다. 가입연령 밖이면 null이고 사유가 premium_note에 온다. */
  premium: number | null;
  /** 여행일수를 곱한 총액 — 화면에는 이 값을 보여준다. */
  premium_total: number | null;
  premium_days: number | null;
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
  premium: number;
  premium_total: number;
  age_range: string | null;
}

export interface PremiumComparisonOut {
  age: number;
  sex: string;
  basis: string | null;
  source: string | null;
  source_url: string | null;
  collected_at: string | null;
  days: number;
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

  getInsurerTiers: () => request<InsurerTierOut[]>("/insurers/ranking-tiers"),

  getIncidentTypes: () => request<IncidentTypeOut[]>("/incidents/types"),

  getPremiumComparison: (age: number, sex: string, days: number, order: "asc" | "desc") =>
    request<PremiumComparisonOut>(`/insurers/premiums?age=${age}&sex=${sex}&days=${days}&order=${order}`),

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
};
