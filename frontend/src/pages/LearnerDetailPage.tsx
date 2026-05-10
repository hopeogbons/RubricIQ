import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "@/components/StatusBadge";
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
import { getLearner, learnerKey } from "@/lib/learners";
import { formatScore } from "@/lib/submissions";

function isNotFound(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404;
}

function formatDate(value: string | null): string {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export function LearnerDetailPage(): JSX.Element {
  const params = useParams<{ id: string }>();
  const id = params.id ?? "";

  const { data, isLoading, error } = useQuery({
    queryKey: learnerKey(id),
    queryFn: () => getLearner(id),
    enabled: id.length > 0,
  });

  if (isLoading) {
    return (
      <div className="container py-8" data-testid="learner-loading">
        <Skeleton className="mb-2 h-8 w-1/3" />
        <Skeleton className="mb-6 h-4 w-1/4" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error) {
    if (isNotFound(error)) {
      return (
        <div className="container py-8">
          <Alert data-testid="learner-not-found">
            <AlertTitle>Learner not found</AlertTitle>
            <AlertDescription>
              This learner does not exist or you do not have access.
            </AlertDescription>
          </Alert>
        </div>
      );
    }
    return (
      <div className="container py-8">
        <Alert variant="destructive" data-testid="learner-error">
          <AlertDescription>
            {extractErrorMessage(error, "Failed to load learner.")}
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

  const submissions = data.submissions;

  return (
    <div className="container py-8">
      <div className="mb-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/rubrics/${data.rubric_id}`}>&larr; Back to rubric</Link>
        </Button>
      </div>

      <header className="mb-6">
        <h1 className="text-2xl font-semibold" data-testid="learner-full-name">
          {data.full_name}
        </h1>
        <p className="text-sm text-muted-foreground">
          <span data-testid="learner-email">{data.email ?? "no email"}</span>
          {data.cohort ? (
            <>
              {" · "}
              <span data-testid="learner-cohort">{data.cohort}</span>
            </>
          ) : null}
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Submissions</CardTitle>
          <CardDescription>
            All evaluation attempts for this learner.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {submissions.length === 0 ? (
            <p
              className="text-sm text-muted-foreground"
              data-testid="submissions-empty"
            >
              No submissions yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Evaluated</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Notes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {submissions.map((s) => (
                  <TableRow key={s.id} data-testid={`submission-row-${s.id}`}>
                    <TableCell>
                      <StatusBadge status={s.status} />
                    </TableCell>
                    <TableCell data-testid={`submission-score-${s.id}`}>
                      {formatScore(s.total_score, s.max_total)}
                    </TableCell>
                    <TableCell>{formatDate(s.evaluated_at)}</TableCell>
                    <TableCell>{formatDate(s.created_at)}</TableCell>
                    <TableCell className="max-w-xs truncate text-xs text-muted-foreground">
                      {s.error_message ?? ""}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
