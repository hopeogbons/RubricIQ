import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { HistogramBucket } from "@/lib/dashboard";

interface ScoreHistogramProps {
  buckets: HistogramBucket[];
}

export function ScoreHistogram({ buckets }: ScoreHistogramProps): JSX.Element {
  const total = buckets.reduce((acc, b) => acc + b.count, 0);
  if (total === 0) {
    return (
      <p
        className="text-sm text-muted-foreground"
        data-testid="score-histogram-empty"
      >
        No completed submissions yet.
      </p>
    );
  }
  return (
    <div className="h-64 w-full" data-testid="score-histogram">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={buckets}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="count" fill="#0f172a" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
