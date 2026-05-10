import { api } from "@/lib/api";
import type { SubmissionSummary } from "@/lib/submissions";

export interface Learner {
  id: string;
  rubric_id: string;
  full_name: string;
  email: string | null;
  cohort: string | null;
  created_at: string;
}

export interface LearnerDetail extends Learner {
  submissions: SubmissionSummary[];
}

export interface LearnerCreatePayload {
  full_name: string;
  email?: string;
  cohort?: string;
}

export const learnersByRubricKey = (rubricId: string) =>
  ["rubrics", rubricId, "learners"] as const;
export const learnerKey = (id: string) => ["learners", id] as const;

export async function listLearners(rubricId: string): Promise<Learner[]> {
  const resp = await api.get<Learner[]>(`/rubrics/${rubricId}/learners`);
  return resp.data;
}

export async function getLearner(id: string): Promise<LearnerDetail> {
  const resp = await api.get<LearnerDetail>(`/learners/${id}`);
  return resp.data;
}

export async function createLearner(
  rubricId: string,
  payload: LearnerCreatePayload,
): Promise<Learner> {
  const resp = await api.post<Learner>(`/rubrics/${rubricId}/learners`, payload);
  return resp.data;
}
