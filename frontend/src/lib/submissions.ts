import { api } from "@/lib/api";
import type { Artifact } from "@/lib/artifacts";

export type SubmissionStatus = "draft" | "processing" | "complete" | "failed";

export interface SubmissionSummary {
  id: string;
  status: SubmissionStatus;
  triggered_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
  total_score: number | null;
  max_total: number | null;
  evaluated_at: string | null;
}

export interface EvaluationScore {
  id: string;
  criterion: string;
  score: number;
  max_score: number;
  explanation: string | null;
}

export interface Evaluation {
  id: string;
  submission_id: string;
  total_score: number | null;
  max_total: number | null;
  evaluated_at: string;
  scores: EvaluationScore[];
}

export interface SubmissionDetail {
  id: string;
  learner_id: string;
  rubric_id: string;
  status: SubmissionStatus;
  triggered_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_by: string | null;
  created_at: string;
  artifacts: Artifact[];
  evaluation: Evaluation | null;
}

export const submissionKey = (id: string) => ["submissions", id] as const;

export async function createSubmission(learnerId: string): Promise<SubmissionDetail> {
  const resp = await api.post<SubmissionDetail>(`/learners/${learnerId}/submissions`, {});
  return resp.data;
}

export async function getSubmission(id: string): Promise<SubmissionDetail> {
  const resp = await api.get<SubmissionDetail>(`/submissions/${id}`);
  return resp.data;
}

export async function evaluateSubmission(id: string): Promise<SubmissionDetail> {
  const resp = await api.post<SubmissionDetail>(`/submissions/${id}/evaluate`, {});
  return resp.data;
}

export function formatScore(score: number | null, max: number | null): string {
  if (score === null || max === null) return "-";
  const fmt = (n: number) => (Number.isInteger(n) ? n.toString() : n.toFixed(1));
  return `${fmt(score)} / ${fmt(max)}`;
}
