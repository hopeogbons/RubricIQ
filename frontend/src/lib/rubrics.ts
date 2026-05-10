import { api } from "@/lib/api";

export interface Rubric {
  id: string;
  unique_name: string;
  display_name: string;
  description: string | null;
  google_sheet_id: string | null;
  google_drive_folder_path: string | null;
  created_by: string | null;
  created_at: string;
}

export interface RubricDetail extends Rubric {
  learner_count: number;
  submission_count: number;
  completion_rate: number;
}

export interface RubricCreatePayload {
  unique_name: string;
  display_name: string;
  description?: string;
  google_sheet_id?: string;
  google_drive_folder_path?: string;
}

export const rubricsKey = ["rubrics"] as const;
export const rubricKey = (id: string) => ["rubrics", id] as const;

export async function listRubrics(): Promise<Rubric[]> {
  const resp = await api.get<Rubric[]>("/rubrics");
  return resp.data;
}

export async function getRubric(id: string): Promise<RubricDetail> {
  const resp = await api.get<RubricDetail>(`/rubrics/${id}`);
  return resp.data;
}

export async function createRubric(payload: RubricCreatePayload): Promise<Rubric> {
  const resp = await api.post<Rubric>("/rubrics", payload);
  return resp.data;
}

export function formatCompletionRate(rate: number): string {
  if (!Number.isFinite(rate)) return "-";
  const pct = rate * 100;
  return `${pct % 1 === 0 ? pct.toFixed(0) : pct.toFixed(1)}%`;
}

export const UNIQUE_NAME_REGEX = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
