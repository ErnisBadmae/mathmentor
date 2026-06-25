export type Subject = 'math_profile' | 'informatics';
export type ErrorCategory =
  | 'arithmetic'
  | 'sign_transfer'
  | 'odz_logic'
  | 'condition_reading'
  | 'probability_double_count'
  | 'unknown_method'
  | 'algorithm_logic'
  | 'code_syntax'
  | 'code_algorithm'
  | 'time_management'
  | 'none'
  | 'other';
export type EvidenceStatus = 'passed' | 'failed' | 'needs_manual_review';
export type ReviewStatus = 'due' | 'done' | 'back_to_work';
export type TopicState = 'open' | 'in_work' | 'under_review' | 'confirmed' | 'back_to_work';

export type Student = {
  id: string;
  display_name: string;
  exam_year: number;
};

export type Track = {
  subject: Subject;
  current_score: number;
  target_score: number;
  score_gap: number;
  phase: string;
};

export type MentorNote = {
  id: string;
  body: string;
  topic_title: string | null;
  source_ref: string | null;
  created_at: string;
  delivered_at: string | null;
};

export type Dashboard = {
  tracks: Track[];
  clean_sheet_ratio: number;
  top_errors: Array<{ category: ErrorCategory; count: number }>;
  due_reviews: number;
  mentor_notes: MentorNote[];
};

export type TopicLifecycle = {
  topic_id: string;
  topic_title: string;
  subject: Subject;
  task_number: string | null;
  state: TopicState;
  active_missions: number;
  passed: boolean;
  reviews_due: number;
  reviews_due_today: number;
  reviews_done: number;
  back_to_work_reviews: number;
  error_count: number;
  attempts_count: number;
  solved_count: number;
  tasks_in_bank: number;
  top_error_category: ErrorCategory | null;
  last_activity_at: string | null;
};

export type ProgramTopic = {
  topic_id: string;
  topic_title: string;
  subject: Subject;
  task_number: string | null;
  state: TopicState;
  error_count: number;
  reviews_due_today: number;
  tasks_in_bank: number;
  solved_count: number;
  attempts_count: number;
  percent: number | null;
};

export type ProgramPhase = {
  key: string;
  label: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  percent: number;
  coverage: { confirmed: number; in_progress: number; under_review: number; open: number; total: number };
  topics: ProgramTopic[];
};

export type Diagnostic = {
  occurred_on: string;
  subject: Subject;
  label: string;
  tasks_total: number;
  tasks_correct: number;
  percent: number;
  note: string | null;
};

export type Mission = {
  id: string;
  subject: Subject;
  title: string;
  instructions: string;
  statement: string | null;
  threshold_percent: number;
  due_date: string | null;
  timebox_minutes: number | null;
};

export type MissionDraft = {
  subject: Subject;
  title: string;
  instructions?: string;
  threshold_percent?: number;
  topic_id?: string | null;
  task_id?: string | null;
  due_date?: string | null;
  timebox_minutes?: number | null;
};

export type ErrorEvent = {
  id: string;
  subject: Subject;
  topic_title: string | null;
  category: ErrorCategory;
  detail: string;
  created_at: string;
  source_ref: string | null;
};

export type ReviewItem = {
  id: string;
  topic_title: string;
  subject: Subject;
  due_date: string;
  status: ReviewStatus;
};

export type ManualReview = {
  id: string;
  attempt_id: string;
  mission_id: string;
  mission_title: string;
  topic_id: string | null;
  topic_title: string | null;
  status: EvidenceStatus;
  score_percent: number;
  tasks_total: number | null;
  tasks_correct: number | null;
  error_category: ErrorCategory;
  feedback: string;
  next_action: string;
  model_id: string;
  prompt_version: string;
  rubric_version: string;
  created_at: string;
};

export type ScoreEventDraft = {
  subject: Subject;
  score: number;
  kind?: string;
  occurred_on?: string | null;
  note?: string | null;
};

export type ScoreEvent = {
  id: string;
  student_id: string;
  subject: Subject;
  score: number;
  kind: string;
  occurred_on: string;
  note: string | null;
};

export type SubmitAttemptPayload = {
  mission_id: string;
  kind: 'text' | 'code' | 'photo' | 'mixed';
  mode: 'clean_sheet' | 'with_hint' | 'unknown';
  answer_text?: string;
  code_text?: string;
  time_spent_minutes?: number;
  tasks_total?: number;
  tasks_correct?: number;
};

export type SubmitAttemptResult = {
  attempt_id: string;
  evidence_id: string;
  status: EvidenceStatus;
  score_percent: number;
  tasks_total: number | null;
  tasks_correct: number | null;
  error_category: ErrorCategory;
  feedback: string;
  next_action: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8001/api';
const BUNDLED_API_TOKEN = import.meta.env.VITE_API_TOKEN ?? '';
const TOKEN_KEY = 'egeMentorApiToken';
const OPERATOR_MODE_KEY = 'egeMentorOperatorMode';

export function getStoredApiToken(): string {
  return BUNDLED_API_TOKEN || localStorage.getItem(TOKEN_KEY) || '';
}

export function setStoredApiToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getOperatorMode(): boolean {
  return localStorage.getItem(OPERATOR_MODE_KEY) === '1';
}

export function setOperatorMode(enabled: boolean): void {
  localStorage.setItem(OPERATOR_MODE_KEY, enabled ? '1' : '0');
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getStoredApiToken();
  const headers = new Headers(init?.headers);
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('X-EGE-MENTOR-TOKEN', token);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let message = `API ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      message = await response.text();
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function getCurrentStudent(): Promise<Student> {
  return request<Student>('/students/current');
}

export function getDashboard(studentId: string): Promise<Dashboard> {
  return request<Dashboard>(`/students/${studentId}/dashboard`);
}

export function getTodayMissions(studentId: string): Promise<Mission[]> {
  return request<Mission[]>(`/students/${studentId}/missions/today`);
}

export function createMission(studentId: string, payload: MissionDraft): Promise<Mission> {
  return request<Mission>(`/students/${studentId}/missions`, {
    method: 'POST',
    body: JSON.stringify({ ...payload, student_id: studentId }),
  });
}

export function updateMission(missionId: string, payload: Partial<MissionDraft>): Promise<Mission> {
  return request<Mission>(`/missions/${missionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function getTopicLifecycle(studentId: string): Promise<TopicLifecycle[]> {
  return request<TopicLifecycle[]>(`/students/${studentId}/topics/lifecycle`);
}

export function getProgram(studentId: string): Promise<ProgramPhase[]> {
  return request<ProgramPhase[]>(`/students/${studentId}/program`);
}

export function getDiagnostics(studentId: string): Promise<Diagnostic[]> {
  return request<Diagnostic[]>(`/students/${studentId}/diagnostics`);
}

export function getErrors(studentId: string): Promise<ErrorEvent[]> {
  return request<ErrorEvent[]>(`/students/${studentId}/errors`);
}

export function getReviews(studentId: string): Promise<ReviewItem[]> {
  return request<ReviewItem[]>(`/students/${studentId}/reviews?due_only=false`);
}

export function markReviewResult(reviewId: string, passed: boolean): Promise<ReviewItem> {
  return request<ReviewItem>(`/reviews/${reviewId}/result`, {
    method: 'POST',
    body: JSON.stringify({ passed }),
  });
}

export function getManualReviews(studentId: string): Promise<ManualReview[]> {
  return request<ManualReview[]>(`/students/${studentId}/manual-reviews`);
}

export function applyManualDecision(
  evidenceId: string,
  status: Exclude<EvidenceStatus, 'needs_manual_review'>,
  extras?: { tasks_total?: number; tasks_correct?: number; score_percent?: number },
): Promise<SubmitAttemptResult> {
  return request<SubmitAttemptResult>(`/evidence/${evidenceId}/manual-decision`, {
    method: 'POST',
    body: JSON.stringify({ status, ...extras }),
  });
}

export function submitAttempt(payload: SubmitAttemptPayload): Promise<SubmitAttemptResult> {
  return request<SubmitAttemptResult>('/attempts', { method: 'POST', body: JSON.stringify(payload) });
}

export function recordScoreEvent(studentId: string, payload: ScoreEventDraft): Promise<ScoreEvent> {
  return request<ScoreEvent>(`/students/${studentId}/score-events`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function publishMentorNote(
  studentId: string,
  payload: { body: string; topic_id?: string | null },
): Promise<MentorNote> {
  return request<MentorNote>(`/students/${studentId}/mentor-notes`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export type SliceTask = {
  task_id: string;
  task_number: string | null;
  statement: string;
};

export type SliceResult = {
  tasks_total: number;
  tasks_correct: number;
  percent: number;
  passed: boolean;
  items: Array<{ task_id: string; correct: boolean }>;
};

export function drawSlice(
  studentId: string,
  subject: Subject,
  size: number,
  topicId?: string | null,
): Promise<{ subject: Subject; items: SliceTask[] }> {
  const topicParam = topicId ? `&topic_id=${topicId}` : '';
  return request<{ subject: Subject; items: SliceTask[] }>(
    `/students/${studentId}/slices/draw?subject=${subject}&size=${size}${topicParam}`,
  );
}

export function gradeSlice(
  studentId: string,
  payload: { subject: Subject; items: Array<{ task_id: string; answer_text: string }> },
): Promise<SliceResult> {
  return request<SliceResult>(`/students/${studentId}/slices/grade`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
