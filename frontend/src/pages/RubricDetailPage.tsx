import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { Link, useParams } from "react-router-dom";

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
import { extractErrorMessage } from "@/lib/api";
import { formatCompletionRate, getRubric, rubricKey } from "@/lib/rubrics";

function isNotFound(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404;
}

export function RubricDetailPage(): JSX.Element {
  const params = useParams<{ id: string }>();
  const id = params.id ?? "";

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

      <section className="mb-8 grid grid-cols-3 gap-4">
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
      </section>

      <Card data-testid="learners-placeholder">
        <CardHeader>
          <CardTitle>Learners</CardTitle>
          <CardDescription>
            The learner table and add-learner flow ship in the next step.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Coming soon.
        </CardContent>
      </Card>
    </div>
  );
}
