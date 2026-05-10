import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { Link, useNavigate, useParams } from "react-router-dom";

import { CriterionAveragesChart } from "@/components/charts/CriterionAveragesChart";
import { ScoreHistogram } from "@/components/charts/ScoreHistogram";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { extractErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  getRubricChartStats,
  rubricChartStatsKey,
} from "@/lib/dashboard";
import {
  learnersByRubricKey,
  listLearners,
  type Learner,
} from "@/lib/learners";
import { formatCompletionRate, getRubric, rubricKey } from "@/lib/rubrics";
import { formatScore } from "@/lib/submissions";

function isNotFound(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404;
}

function canAddLearner(role: string): boolean {
  return role === "admin" || role === "superadmin" || role === "evaluator";
}

function formatDate(value: string): string {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString();
}

interface LearnersSectionProps {
  rubricId: string;
  canAdd: boolean;
}

function LearnersSection({ rubricId, canAdd }: LearnersSectionProps): JSX.Element {
  const navigate = useNavigate();
  const { data, isLoading, error } = useQuery({
    queryKey: learnersByRubricKey(rubricId),
    queryFn: () => listLearners(rubricId),
  });

  return (
    <Card data-testid="learners-section">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Learners</CardTitle>
          <CardDescription>People being evaluated against this rubric.</CardDescription>
        </div>
        {canAdd ? (
          <Button asChild data-testid="add-learner-button">
            <Link to={`/rubrics/${rubricId}/learners/new`}>Add learner</Link>
          </Button>
        ) : null}
      </CardHeader>
      <CardContent>
        {error ? (
          <Alert variant="destructive" data-testid="learners-error">
            <AlertDescription>
              {extractErrorMessage(error, "Failed to load learners.")}
            </AlertDescription>
          </Alert>
        ) : isLoading ? (
          <div className="space-y-2" data-testid="learners-loading">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : !data || data.length === 0 ? (
          <p className="text-sm text-muted-foreground" data-testid="learners-empty">
            No learners yet.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Cohort</TableHead>
                <TableHead>Added</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((learner: Learner) => (
                <TableRow
                  key={learner.id}
                  data-testid={`learner-row-${learner.id}`}
                  className="cursor-pointer"
                  onClick={() => navigate(`/learners/${learner.id}`)}
                >
                  <TableCell className="font-medium">{learner.full_name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {learner.email ?? "-"}
                  </TableCell>
                  <TableCell>{learner.cohort ?? "-"}</TableCell>
                  <TableCell>{formatDate(learner.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

export function RubricDetailPage(): JSX.Element {
  const params = useParams<{ id: string }>();
  const id = params.id ?? "";
  const { user } = useAuth();
  const canAdd = user ? canAddLearner(user.role) : false;

  const { data, isLoading, error } = useQuery({
    queryKey: rubricKey(id),
    queryFn: () => getRubric(id),
    enabled: id.length > 0,
  });

  if (isLoading) {
    return (
      <div className="container py-8" data-testid="rubric-loading">
        <Skeleton className="mb-2 h-8 w-1/3" />
        <Skeleton className="mb-6 h-4 w-1/4" />
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      </div>
    );
  }

  if (error) {
    if (isNotFound(error)) {
      return (
        <div className="container py-8">
          <Alert data-testid="rubric-not-found">
            <AlertTitle>Rubric not found</AlertTitle>
            <AlertDescription>
              This rubric does not exist or you do not have access.{" "}
              <Link to="/rubrics" className="underline">
                Back to rubrics
              </Link>
            </AlertDescription>
          </Alert>
        </div>
      );
    }
    return (
      <div className="container py-8">
        <Alert variant="destructive" data-testid="rubric-error">
          <AlertDescription>
            {extractErrorMessage(error, "Failed to load rubric.")}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container py-8 text-sm text-muted-foreground">No data.</div>
    );
  }

  return (
    <div className="container py-8">
      <div className="mb-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/rubrics">&larr; Back to rubrics</Link>
        </Button>
      </div>

      <header className="mb-6">
        <h1 className="text-2xl font-semibold" data-testid="rubric-display-name">
          {data.display_name}
        </h1>
        <p className="font-mono text-xs text-muted-foreground" data-testid="rubric-unique-name">
          {data.unique_name}
        </p>
        {data.description ? (
          <p className="mt-3 text-sm" data-testid="rubric-description">
            {data.description}
          </p>
        ) : null}
      </header>

      <section className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Learners</CardDescription>
            <CardTitle className="text-3xl" data-testid="stat-learner-count">
              {data.learner_count}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Submissions</CardDescription>
            <CardTitle className="text-3xl" data-testid="stat-submission-count">
              {data.submission_count}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Completion rate</CardDescription>
            <CardTitle className="text-3xl" data-testid="stat-completion-rate">
              {formatCompletionRate(data.completion_rate)}
            </CardTitle>
          </CardHeader>
        </Card>
        <ChartAverageScoreCard rubricId={id} />
      </section>

      <ChartsSection rubricId={id} />

      <LearnersSection rubricId={id} canAdd={canAdd} />
    </div>
  );
}

function ChartAverageScoreCard({ rubricId }: { rubricId: string }): JSX.Element {
  const { data, isLoading } = useQuery({
    queryKey: rubricChartStatsKey(rubricId),
    queryFn: () => getRubricChartStats(rubricId),
  });
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>Avg total score</CardDescription>
        <CardTitle className="text-3xl" data-testid="stat-average-total">
          {isLoading ? "..." : formatScore(data?.average_total_score ?? null, data?.average_max_total ?? null)}
        </CardTitle>
      </CardHeader>
    </Card>
  );
}

function ChartsSection({ rubricId }: { rubricId: string }): JSX.Element {
  const { data, isLoading, error } = useQuery({
    queryKey: rubricChartStatsKey(rubricId),
    queryFn: () => getRubricChartStats(rubricId),
  });

  return (
    <section
      className="mb-8 grid grid-cols-1 gap-4 lg:grid-cols-2"
      data-testid="charts-section"
    >
      <Card>
        <CardHeader>
          <CardTitle>Score distribution</CardTitle>
          <CardDescription>
            Total score as a percentage of the rubric max.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <Alert variant="destructive" data-testid="charts-error">
              <AlertDescription>
                {extractErrorMessage(error, "Failed to load chart data.")}
              </AlertDescription>
            </Alert>
          ) : isLoading || !data ? (
            <Skeleton className="h-64 w-full" data-testid="histogram-loading" />
          ) : (
            <ScoreHistogram buckets={data.score_distribution} />
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Per-criterion averages</CardTitle>
          <CardDescription>
            Average score for each rubric criterion across completed submissions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error ? null : isLoading || !data ? (
            <Skeleton className="h-64 w-full" data-testid="criterion-loading" />
          ) : (
            <CriterionAveragesChart averages={data.criterion_averages} />
          )}
        </CardContent>
      </Card>
    </section>
  );
}
