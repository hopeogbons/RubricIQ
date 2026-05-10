import { api } from "@/lib/api";

export interface GlobalStats {
  total_rubrics: number;
  total_learners: number;
  total_submissions: number;
  completion_rate: number;
}

export interface HistogramBucket {
  bucket: string;
  count: number;
}

export interface CriterionAverage {
  criterion: string;
  average: number;
  max_score_average: number;
  count: number;
}

export interface RubricChartStats {
  rubric_id: string;
  average_total_score: number | null;
  average_max_total: number | null;
  score_distribution: HistogramBucket[];
  criterion_averages: CriterionAverage[];
}

export const globalStatsKey = ["dashboard", "stats"] as const;
export const rubricChartStatsKey = (id: string) =>
  ["dashboard", "rubrics", id] as const;

export async function getGlobalStats(): Promise<GlobalStats> {
  const resp = await api.get<GlobalStats>("/dashboard/stats");
  return resp.data;
}

export async function getRubricChartStats(id: string): Promise<RubricChartStats> {
  const resp = await api.get<RubricChartStats>(`/dashboard/rubrics/${id}/stats`);
  return resp.data;
}
