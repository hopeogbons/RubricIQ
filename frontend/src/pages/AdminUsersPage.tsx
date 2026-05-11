import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { activateUser, listUsers, usersKey } from "@/lib/admin";
import { useAuth, type User } from "@/lib/auth";
import { useToast } from "@/lib/toast";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 10;

type SortColumn = "email" | "full_name" | "role" | "is_active" | "created_at";
type SortDirection = "asc" | "desc";

interface SortState {
  column: SortColumn;
  direction: SortDirection;
}

function isAdminRole(role: string): boolean {
  return role === "admin" || role === "superadmin";
}

function compareValues(a: unknown, b: unknown, direction: SortDirection): number {
  const sign = direction === "asc" ? 1 : -1;
  const aNil = a === null || a === undefined || a === "";
  const bNil = b === null || b === undefined || b === "";
  if (aNil && bNil) return 0;
  if (aNil) return 1; // nulls always last
  if (bNil) return -1;
  if (typeof a === "boolean" && typeof b === "boolean") {
    return sign * (Number(a) - Number(b));
  }
  return sign * String(a).localeCompare(String(b));
}

function formatDate(value: string | null): string {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function UserStatusBadge({ active }: { active: boolean }): JSX.Element {
  return (
    <span
      data-testid={`user-status-${active ? "active" : "pending"}`}
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
        active
          ? "bg-green-100 text-green-800"
          : "bg-amber-100 text-amber-800",
      )}
    >
      {active ? "Active" : "Pending"}
    </span>
  );
}

function SortHeader({
  label,
  column,
  sort,
  onChange,
}: {
  label: string;
  column: SortColumn;
  sort: SortState;
  onChange: (next: SortState) => void;
}): JSX.Element {
  const isActive = sort.column === column;
  const arrow = isActive ? (sort.direction === "asc" ? "▲" : "▼") : "";
  return (
    <TableHead>
      <button
        type="button"
        data-testid={`sort-${column}`}
        className="flex items-center gap-1 font-medium text-muted-foreground hover:text-foreground"
        onClick={() =>
          onChange({
            column,
            direction: isActive && sort.direction === "asc" ? "desc" : "asc",
          })
        }
      >
        {label}
        <span className="text-[10px]">{arrow}</span>
      </button>
    </TableHead>
  );
}

export function AdminUsersPage(): JSX.Element {
  const { user } = useAuth();
  if (!user || !isAdminRole(user.role)) {
    return <Navigate to="/rubrics" replace />;
  }
  return <UsersTable />;
}

function UsersTable(): JSX.Element {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortState>({
    column: "created_at",
    direction: "desc",
  });
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useQuery({
    queryKey: usersKey,
    queryFn: listUsers,
  });

  const mutation = useMutation({
    mutationFn: (id: string) => activateUser(id),
    onSuccess: async (updated) => {
      pushToast(
        `Activated ${updated.email}. Activation email queued.`,
        "success",
      );
      await queryClient.invalidateQueries({ queryKey: usersKey });
    },
    onError: (err) => {
      pushToast(extractErrorMessage(err, "Activation failed."), "destructive");
    },
  });

  const filtered = useMemo(() => {
    if (!data) return [] as User[];
    const needle = search.trim().toLowerCase();
    if (!needle) return data;
    return data.filter((u) => {
      const haystack = [u.email, u.full_name ?? "", u.role].join(" ").toLowerCase();
      return haystack.includes(needle);
    });
  }, [data, search]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) =>
      compareValues(a[sort.column], b[sort.column], sort.direction),
    );
    return copy;
  }, [filtered, sort]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const start = (safePage - 1) * PAGE_SIZE;
  const pageRows = sorted.slice(start, start + PAGE_SIZE);

  return (
    <div className="container py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Users</h1>
        <p className="text-sm text-muted-foreground">
          Activate pending accounts and review user roles.
        </p>
      </header>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <div>
            <CardTitle>All users</CardTitle>
            <CardDescription>
              {sorted.length} of {data?.length ?? 0}
            </CardDescription>
          </div>
          <Input
            data-testid="user-search"
            placeholder="Search email, name, or role"
            className="max-w-sm"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </CardHeader>
        <CardContent>
          {error ? (
            <Alert variant="destructive" data-testid="users-error">
              <AlertDescription>
                {extractErrorMessage(error, "Failed to load users.")}
              </AlertDescription>
            </Alert>
          ) : isLoading ? (
            <div className="space-y-2" data-testid="users-loading">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : sorted.length === 0 ? (
            <p
              className="text-sm text-muted-foreground"
              data-testid="users-empty"
            >
              No users match.
            </p>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <SortHeader
                      label="Email"
                      column="email"
                      sort={sort}
                      onChange={setSort}
                    />
                    <SortHeader
                      label="Full name"
                      column="full_name"
                      sort={sort}
                      onChange={setSort}
                    />
                    <SortHeader
                      label="Role"
                      column="role"
                      sort={sort}
                      onChange={setSort}
                    />
                    <SortHeader
                      label="Status"
                      column="is_active"
                      sort={sort}
                      onChange={setSort}
                    />
                    <SortHeader
                      label="Created"
                      column="created_at"
                      sort={sort}
                      onChange={setSort}
                    />
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pageRows.map((u) => (
                    <TableRow key={u.id} data-testid={`user-row-${u.id}`}>
                      <TableCell className="font-medium">{u.email}</TableCell>
                      <TableCell>{u.full_name ?? "-"}</TableCell>
                      <TableCell>{u.role}</TableCell>
                      <TableCell>
                        <UserStatusBadge active={u.is_active} />
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDate(u.created_at)}
                      </TableCell>
                      <TableCell>
                        {u.is_active ? (
                          <span className="text-xs text-muted-foreground">-</span>
                        ) : (
                          <Button
                            size="sm"
                            data-testid={`activate-${u.id}`}
                            disabled={
                              mutation.isPending &&
                              mutation.variables === u.id
                            }
                            onClick={() => mutation.mutate(u.id)}
                          >
                            {mutation.isPending && mutation.variables === u.id
                              ? "Activating..."
                              : "Activate"}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div
                className="mt-4 flex items-center justify-between text-sm"
                data-testid="pagination"
              >
                <span className="text-muted-foreground">
                  Page {safePage} of {totalPages}
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    data-testid="page-prev"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={safePage <= 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    data-testid="page-next"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={safePage >= totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
