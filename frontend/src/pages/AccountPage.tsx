import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/lib/auth";

function formatDate(value: string | null): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

export function AccountPage(): JSX.Element {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    return (
      <div className="container py-12 text-sm text-muted-foreground">
        Loading account...
      </div>
    );
  }

  const handleLogout = (): void => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="container flex justify-center py-12">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle>Your account</CardTitle>
          <CardDescription>Read-only profile from RubricIQ.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-3 gap-y-3 text-sm">
            <dt className="font-medium text-muted-foreground">Email</dt>
            <dd className="col-span-2" data-testid="account-email">{user.email}</dd>

            <dt className="font-medium text-muted-foreground">Full name</dt>
            <dd className="col-span-2" data-testid="account-full-name">
              {user.full_name ?? "-"}
            </dd>

            <dt className="font-medium text-muted-foreground">Role</dt>
            <dd className="col-span-2" data-testid="account-role">{user.role}</dd>

            <dt className="font-medium text-muted-foreground">Status</dt>
            <dd className="col-span-2">{user.is_active ? "Active" : "Inactive"}</dd>

            <dt className="font-medium text-muted-foreground">Activated</dt>
            <dd className="col-span-2">{formatDate(user.activated_at)}</dd>

            <dt className="font-medium text-muted-foreground">Created</dt>
            <dd className="col-span-2">{formatDate(user.created_at)}</dd>
          </dl>
        </CardContent>
        <CardFooter>
          <Button variant="outline" onClick={handleLogout}>
            Log out
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
