import { useQuery } from "@tanstack/react-query";
import { Link, Navigate } from "react-router-dom";

import { Alert, AlertDescription } from "@/components/ui/alert";
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
  getGlobalStats,
  globalStatsKey,
} from "@/lib/dashboard";
import { formatCompletionRate, listRubrics, rubricsKey } from "@/lib/rubrics";

function isAdminRole(role: string): boolean {
  return role === "admin" || role === "superadmin";
}

export function DashboardPage(): JSX.Element {
  const { user } = useAuth();
  if (!user || !isAdminRole(user.role)) {
    return <Navigate to="/rubrics" replace />;
  }
  return <AdminDashboard />;
}

function AdminDashboard(): JSX.Element {
  const statsQuery = useQuery({
    queryKey: globalStatsKey,
    queryFn: getGlobalStats,
  });
  const rubricsQuery = useQuery({
    queryKey: rubricsKey,
    queryFn: listRubrics,
  });

  return (
    <div className="container py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Activity across all rubrics.
        </p>
      </header>

      {statsQuery.error ? (
        <Alert variant="destructive" data-testid="dashboard-stats-error">
          <AlertDescription>
            {extractErrorMessage(statsQuery.error, "Failed to load stats.")}
          </AlertDescription>
        </Alert>
      ) : statsQuery.isLoading ? (
        <div className="mb-8 grid grid-cols-4 gap-4" data-testid="dashboard-stats-loading">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : statsQuery.data ? (
        <section className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Rubrics</CardDescription>
              <CardTitle className="text-3xl" data-testid="stat-total-rubrics">
                {statsQuery.data.total_rubrics}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Learners</CardDescription>
              <CardTitle className="text-3xl" data-testid="stat-total-learners">
                {statsQuery.data.total_learners}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Submissions</CardDescription>
              <CardTitle className="text-3xl" data-testid="stat-total-submissions">
                {statsQuery.data.total_submissions}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Completion rate</CardDescription>
              <CardTitle className="text-3xl" data-testid="stat-overall-completion">
                {formatCompletionRate(statsQuery.data.completion_rate)}
              </CardTitle>
            </CardHeader>
          </Card>
        </section>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Rubrics</CardTitle>
          <CardDescription>Open a rubric to see its charts.</CardDescription>
        </CardHeader>
        <CardContent>
          {rubricsQuery.error ? (
            <Alert variant="destructive" data-testid="dashboard-rubrics-error">
              <AlertDescription>
                {extractErrorMessage(rubricsQuery.error, "Failed to load rubrics.")}
              </AlertDescription>
            </Alert>
          ) : rubricsQuery.isLoading ? (
            <div className="space-y-2" data-testid="dashboard-rubrics-loading">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : !rubricsQuery.data || rubricsQuery.data.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="dashboard-rubrics-empty">
              No rubrics yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Unique name</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rubricsQuery.data.map((rubric) => (
                  <TableRow key={rubric.id} data-testid={`dashboard-rubric-${rubric.id}`}>
                    <TableCell className="font-medium">
                      <Link to={`/rubrics/${rubric.id}`} className="hover:underline">
                        {rubric.display_name}
                      </Link>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {rubric.unique_name}
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
