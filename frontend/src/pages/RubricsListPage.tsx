import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { listRubrics, rubricsKey } from "@/lib/rubrics";

function formatDate(value: string): string {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString();
}

function isAdminRole(role: string): boolean {
  return role === "admin" || role === "superadmin";
}

export function RubricsListPage(): JSX.Element {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data, isLoading, error } = useQuery({
    queryKey: rubricsKey,
    queryFn: listRubrics,
  });

  const canCreate = user ? isAdminRole(user.role) : false;

  return (
    <div className="container py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Rubrics</h1>
          <p className="text-sm text-muted-foreground">
            Rubrics you have access to.
          </p>
        </div>
        {canCreate ? (
          <Button asChild data-testid="new-rubric-button">
            <Link to="/rubrics/new">New rubric</Link>
          </Button>
        ) : null}
      </div>

      {error ? (
        <Alert variant="destructive" data-testid="rubrics-error">
          <AlertDescription>
            {extractErrorMessage(error, "Failed to load rubrics.")}
          </AlertDescription>
        </Alert>
      ) : isLoading ? (
        <div className="space-y-2" data-testid="rubrics-loading">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : !data || data.length === 0 ? (
        <Card data-testid="rubrics-empty">
          <CardHeader>
            <CardTitle>No rubrics yet</CardTitle>
            <CardDescription>
              {canCreate
                ? "Create your first rubric to start tracking learners."
                : "An admin needs to create a rubric and grant you access."}
            </CardDescription>
          </CardHeader>
          {canCreate ? (
            <CardContent>
              <Button asChild>
                <Link to="/rubrics/new">New rubric</Link>
              </Button>
            </CardContent>
          ) : null}
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Unique name</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((rubric) => (
                <TableRow
                  key={rubric.id}
                  data-testid={`rubric-row-${rubric.id}`}
                  className="cursor-pointer"
                  onClick={() => navigate(`/rubrics/${rubric.id}`)}
                >
                  <TableCell className="font-medium">{rubric.display_name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {rubric.unique_name}
                  </TableCell>
                  <TableCell>{formatDate(rubric.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
