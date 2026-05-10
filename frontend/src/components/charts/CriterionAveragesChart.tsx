import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { CriterionAverage } from "@/lib/dashboard";

interface CriterionAveragesChartProps {
  averages: CriterionAverage[];
}

interface Row {
  criterion: string;
  average: number;
  max_score_average: number;
  ratio: number;
}

export function CriterionAveragesChart({
  averages,
}: CriterionAveragesChartProps): JSX.Element {
  if (averages.length === 0) {
    return (
      <p
        className="text-sm text-muted-foreground"
        data-testid="criterion-averages-empty"
      >
        No per-criterion data yet.
      </p>
    );
  }
  const rows: Row[] = averages.map((a) => ({
    criterion: a.criterion,
    average: Number(a.average.toFixed(2)),
    max_score_average: Number(a.max_score_average.toFixed(2)),
    ratio: a.max_score_average > 0 ? a.average / a.max_score_average : 0,
  }));
  return (
    <div className="h-64 w-full" data-testid="criterion-averages-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ left: 24 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" allowDecimals tick={{ fontSize: 12 }} />
          <YAxis
            type="category"
            dataKey="criterion"
            width={140}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(_value, _name, item) => {
              const row = item.payload as Row;
              return [`${row.average} / ${row.max_score_average}`, "Score"];
            }}
          />
          <Bar dataKey="average" radius={[0, 4, 4, 0]}>
            {rows.map((r) => (
              <Cell key={r.criterion} fill="#0f172a" />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
