// Typed client for the local Echo UI backend (Echo_UI/backend/app.py).

export type Profile = {
  name: string
  provider: string
  model: string
  description: string
  key_configured: boolean
}

export type Meta = {
  profiles: Profile[]
  default_profile: string
  local_split: Record<string, string> | null
  scope_min: string
  scope_max: string
  suggested_questions: string[]
}

export type Manager = {
  Manager_ID: string
  Manager_Name: string
  Primary_Department: string
  Primary_Team: string
  Pilot_Assigned_Employees: number
}

export type SurveyRow = {
  Survey_Date: string
  Team: string
  Dimension: string
  Responses: number
  Eligible_Employees: number
  Mean_Score: number | null
  Favorable_Percent: number | null
  eNPS_Score: number | null
}

export type Overview = {
  manager: { Manager_ID: string; Manager_Name: string }
  teams: string[]
  scope: Scope
  headcount: number
  contributions: number
  comments: number
  survey: SurveyRow[]
}

export type Scope = { manager_id: string; start_date: string; end_date: string }

export type RunMeta = {
  id: string
  question: string
  typed_question: string
  manager_id: string
  start_date: string
  end_date: string
  mode: 'demo' | 'live' | 'replay' | 'offline'
  profile: string
  replay_of?: string
  recorded_at?: string
  created_at: string
  finished_at?: string
  state: string
  exit_code?: number
  result_status?: string
  verification?: string
  api_calls?: number
  charts?: number
}

export type SqlEvidence = {
  citation_id: string
  producer: string
  sql: string
  rows: Record<string, unknown>[]
  truncated: boolean
}

export type TextEvidence = {
  citation_id: string
  source: string
  record_id: string
  team?: string
  date?: string
  dimension?: string
  anonymous?: boolean
  text: string
}

export type Evidence = SqlEvidence | TextEvidence | (Record<string, unknown> & { citation_id: string })

export type Finding = {
  finding_id: string
  text: string
  citation_ids: string[]
  status: string
  reason: string
  deterministic_issues: unknown[]
  assertions?: {
    assertion_id?: string
    claim: string
    kind: 'factual' | 'proposal'
    citation_ids: string[]
    assessment: 'supported' | 'contradicted' | 'insufficient_evidence'
    reason: string
  }[]
}

export type Review = {
  version?: string
  correction_judgments?: Record<string, { mandatory: boolean; addressed: boolean; reason: string }>
  decision: string
  ratings: Record<string, { score: number; rationale: string }>
  issues: unknown[]
  uncertainty: string
  deterministic_issues: unknown[]
  mode: string
  findings: Finding[]
  repair_targets: unknown[]
  clarification_question: string | null
}

export type ChartSpec = {
  source_id: string
  kind: string
  x: string
  y: string
  series?: string
  title: string
  x_label: string
  y_label: string
  unit?: string
  denominator?: string
}

export type Artifact = {
  agent: string
  question: string
  answer: string
  scope: Scope
  evidence: Evidence[]
  mode: string
  status: string
  verification: { decision?: string; status?: string; reviews?: Review[]; drafts_checked?: number; completed_reviews?: number; latest_candidate_id?: string; released_candidate_id?: string }
  delegations: { agent: string; question: string; answer: string; evidence: Evidence[] }[]
  visualization: { charts?: ChartSpec[]; reason?: string; files?: { source_id: string; svg: string; csv: string; metadata: string }[] }
  rag: Record<string, unknown>
  execution: { generation_api_calls?: number; successful_generation_api_calls?: number; profiles_used?: Record<string, { model: string; api_calls: number }> }
  capture?: { run_id?: string; exchanges?: string; resume_checkpoint?: string | null; parent_run_id?: string; source_checkpoint?: string; phase_only?: boolean }
  sentiment: Record<string, unknown>
  findings: Finding[]
  limitations: string[]
  next_steps: string[]
  clarification_questions: string[]
  failure: Record<string, unknown>
  made?: Made
  triangle?: Triangle
  examples?: Example[]
  watch?: WatchItem[]
  voice?: { topic: string; responses: number; positive: number; negative: number }
  guardrail?: { rule: string; checked_by: string; detail: string }
}

export type TriangleSide = { value: string; label: string; tone: 'good' | 'fair' | 'poor' | 'neutral'; agent: string }
export type Triangle = { work: TriangleSide; feedback: TriangleSide; voice: TriangleSide; agreement: 'conflict' | 'aligned'; note: string }
export type Example = { contribution_id: string; employee_id: string; name: string; team_helped: string; date: string; outcome: string; praise_reached_you: boolean }
export type WatchItem = { metric: string; baseline: string; goal: string }

export type Made = {
  specialists: string[]
  queries: number
  survey_sources: number
  sentiment_runs: number
  charts: number
  findings_checked: number
  drafts_checked: number
  completed_reviews?: number
  review_status?: string
}

export type PulseTheme = { text: string; share: 'most' | 'many' | 'some' | 'a few'; tone: 'positive' | 'concern' | 'mixed' }

export type Pulse = {
  scope: Scope
  mood: { topic: string; responses: number; positive: number; neutral: number; negative: number }[]
  themes: { topic: string; headline: string; themes: PulseTheme[]; comments_used: number }[] | null
  generated_at: string | null
  model: string | null
  error: string | null
}

export type RunDetail = { meta: RunMeta; artifact: Artifact | null; console: string }

export type LogEvent = {
  time_utc: string
  run_id: string
  elapsed_seconds: number
  event: string
  agent?: string
  profile?: string
  tool?: string
  tools?: string[]
  error_category?: string
  http_status?: number
  status?: string
  [key: string]: unknown
}

export type Quota = {
  limit_per_model: number
  resets_at: string
  models: { model: string; calls: number; quota_errors: number }[]
  note: string
}

export type TableInfo = {
  name: string
  rows: number
  columns: { Column: string; Meaning: string; Primary_Key: string; References: string; Nullable: string }[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!response.ok) {
    let detail = response.statusText
    try {
      detail = (await response.json()).detail ?? detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.json()
}

export const api = {
  meta: () => request<Meta>('/api/meta'),
  managers: () => request<Manager[]>('/api/managers'),
  overview: (id: string, start: string, end: string) =>
    request<Overview>(`/api/managers/${encodeURIComponent(id)}/overview?start=${start}&end=${end}`),
  tables: () => request<TableInfo[]>('/api/data/tables'),
  quota: () => request<Quota>('/api/quota'),
  runs: () => request<RunMeta[]>('/api/runs'),
  run: (id: string) => request<RunDetail>(`/api/runs/${id}`),
  managerRun: (id: string) => request<RunDetail>(`/api/runs/${id}?view=manager`),
  pulse: (id: string, start: string, end: string, generate = false) =>
    request<Pulse>(`/api/managers/${encodeURIComponent(id)}/pulse?start=${start}&end=${end}${generate ? '&generate=true' : ''}`),
  savedAnswers: (id: string, start: string, end: string) =>
    request<{ question: string; recorded_at: string | null }[]>(`/api/recordings?manager_id=${encodeURIComponent(id)}&start=${start}&end=${end}`),
  lookupManager: (code: string) => request<Manager>(`/api/manager/${encodeURIComponent(code)}`),
  startRun: (body: Record<string, unknown>) => request<RunMeta>('/api/runs', { method: 'POST', body: JSON.stringify(body) }),
  cancelRun: (id: string) => request<unknown>(`/api/runs/${id}/cancel`, { method: 'POST' }),
  deleteRun: (id: string) => request<unknown>(`/api/runs/${id}`, { method: 'DELETE' }),
  fileUrl: (id: string, path: string) => `/api/runs/${id}/files/${path.split('/').pop()}`,
}

export function isSql(evidence: Evidence): evidence is SqlEvidence {
  return typeof (evidence as SqlEvidence).sql === 'string'
}

export function isText(evidence: Evidence): evidence is TextEvidence {
  return typeof (evidence as TextEvidence).text === 'string'
}
