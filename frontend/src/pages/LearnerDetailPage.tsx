import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Link, useParams } from "react-router-dom";

import { ArtifactPanel } from "@/components/ArtifactPanel";
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
import {
  evaluateSubmission,
  formatScore,
  getSubmission,
  submissionKey,
  type SubmissionDetail,
} from "@/lib/submissions";
import { useToast } from "@/lib/toast";

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

  const learnerQuery = useQuery({
    queryKey: learnerKey(id),
    queryFn: () => getLearner(id),
    enabled: id.length > 0,
  });

  if (learnerQuery.isLoading) {
    return (
      <div className="container py-8" data-testid="learner-loading">
        <Skeleton className="mb-2 h-8 w-1/3" />
        <Skeleton className="mb-6 h-4 w-1/4" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (learnerQuery.error) {
    if (isNotFound(learnerQuery.error)) {
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
            {extractErrorMessage(learnerQuery.error, "Failed to load learner.")}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const data = learnerQuery.data;
  if (!data) {
    return (
      <div className="container py-8 text-sm text-muted-foreground">No data.</div>
    );
  }

  const summary = data.submissions[0] ?? null;

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

      {summary === null ? (
        <Card data-testid="no-submission">
          <CardHeader>
            <CardTitle>No submission yet</CardTitle>
            <CardDescription>
              This learner has not been evaluated. Start one from the rubric page.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link to={`/rubrics/${data.rubric_id}/learners/new`}>
                Add a submission
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <SubmissionSection
          submissionId={summary.id}
          summaryStatus={summary.status}
        />
      )}
    </div>
  );
}

function SubmissionSection({
  submissionId,
  summaryStatus,
}: {
  submissionId: string;
  summaryStatus: SubmissionDetail["status"];
}): JSX.Element {
  const submissionQuery = useQuery({
    queryKey: submissionKey(submissionId),
    queryFn: () => getSubmission(submissionId),
  });
  if (submissionQuery.isLoading || !submissionQuery.data) {
    return <Skeleton className="h-40 w-full" data-testid="submission-loading" />;
  }
  if (submissionQuery.error) {
    return (
      <Alert variant="destructive" data-testid="submission-error">
        <AlertDescription>
          {extractErrorMessage(submissionQuery.error, "Failed to load submission.")}
        </AlertDescription>
      </Alert>
    );
  }
  return (
    <SubmissionBody
      submission={submissionQuery.data}
      summaryStatus={summaryStatus}
    />
  );
}

function SubmissionBody({
  submission,
  summaryStatus,
}: {
  submission: SubmissionDetail;
  summaryStatus: SubmissionDetail["status"];
}): JSX.Element {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const status = submission.status;
  const editable = status !== "processing";
  const canEvaluate = status !== "processing" && submission.artifacts.length > 0;

  const mutation = useMutation({
    mutationFn: () => evaluateSubmission(submission.id),
    onSuccess: async (updated) => {
      pushToast(
        status === "draft"
          ? "Evaluation started."
          : "Re-evaluation started.",
        "success",
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: submissionKey(updated.id) }),
        queryClient.invalidateQueries({ queryKey: learnerKey(submission.learner_id) }),
      ]);
    },
    onError: (err) => {
      pushToast(
        extractErrorMessage(err, "Failed to start evaluation."),
        "destructive",
      );
    },
  });

  return (
    <div className="space-y-6">
      <Card data-testid="submission-summary">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-3">
              Submission <StatusBadge status={status} />
            </CardTitle>
            <CardDescription>
              Created {formatDate(submission.created_at)}
              {submission.evaluation ? (
                <>
                  {" "}
                  · Score:{" "}
                  <span data-testid="submission-score">
                    {formatScore(
                      submission.evaluation.total_score,
                      submission.evaluation.max_total,
                    )}
                  </span>
                </>
              ) : null}
            </CardDescription>
          </div>
          <Button
            data-testid="evaluate-button"
            disabled={!canEvaluate || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending
              ? "Starting..."
              : status === "draft"
                ? "Start evaluation"
                : "Re-evaluate"}
          </Button>
        </CardHeader>
        {status === "failed" && submission.error_message ? (
          <CardContent>
            <Alert variant="destructive" data-testid="submission-failure">
              <AlertTitle>Evaluation failed</AlertTitle>
              <AlertDescription>{submission.error_message}</AlertDescription>
            </Alert>
          </CardContent>
        ) : null}
      </Card>

      {submission.evaluation && submission.evaluation.scores.length > 0 ? (
        <Card data-testid="scores-card">
          <CardHeader>
            <CardTitle>Per-criterion scores</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Criterion</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Explanation</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {submission.evaluation.scores.map((s) => (
                  <TableRow key={s.id} data-testid={`score-row-${s.id}`}>
                    <TableCell className="font-medium">{s.criterion}</TableCell>
                    <TableCell>{`${s.score} / ${s.max_score}`}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {s.explanation ?? "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}

      {editable ? (
        <ArtifactPanel
          submissionId={submission.id}
          artifacts={submission.artifacts}
        />
      ) : (
        <Card data-testid="artifacts-readonly">
          <CardHeader>
            <CardTitle>Artifacts</CardTitle>
            <CardDescription>
              Artifacts cannot be changed while the submission is{" "}
              {summaryStatus}.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {submission.artifacts.length === 0 ? (
              <p className="text-sm text-muted-foreground">No artifacts.</p>
            ) : (
              <ul className="divide-y rounded-md border">
                {submission.artifacts.map((a) => (
                  <li
                    key={a.id}
                    data-testid={`readonly-artifact-${a.id}`}
                    className="px-3 py-2 text-sm"
                  >
                    <span className="font-medium">{a.type}</span>
                    {" — "}
                    {a.filename || a.external_url || a.text_value || a.id}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
