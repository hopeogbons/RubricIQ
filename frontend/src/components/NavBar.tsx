import { Link, NavLink, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";

function isAdminRole(role: string): boolean {
  return role === "admin" || role === "superadmin";
}

export function NavBar(): JSX.Element {
  const { status, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = (): void => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="border-b">
      <div className="container flex h-14 items-center justify-between">
        <div className="flex items-center gap-6">
          <Link to="/" className="font-semibold">
            RubricIQ
          </Link>
          {status === "authenticated" ? (
            <nav className="flex items-center gap-4 text-sm">
              <NavLink
                to="/rubrics"
                className={({ isActive }) =>
                  cn(
                    "text-muted-foreground hover:text-foreground",
                    isActive && "text-foreground",
                  )
                }
              >
                Rubrics
              </NavLink>
              {user && isAdminRole(user.role) ? (
                <NavLink
                  to="/dashboard"
                  data-testid="nav-dashboard-link"
                  className={({ isActive }) =>
                    cn(
                      "text-muted-foreground hover:text-foreground",
                      isActive && "text-foreground",
                    )
                  }
                >
                  Dashboard
                </NavLink>
              ) : null}
            </nav>
          ) : null}
        </div>
        <nav className="flex items-center gap-3">
          {status === "authenticated" && user ? (
            <>
              <Link to="/account" className="text-sm">
                {user.email}
              </Link>
              <Button variant="outline" size="sm" onClick={handleLogout}>
                Log out
              </Button>
            </>
          ) : status === "anonymous" ? (
            <>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/login">Log in</Link>
              </Button>
              <Button size="sm" asChild>
                <Link to="/signup">Sign up</Link>
              </Button>
            </>
          ) : null}
        </nav>
      </div>
    </header>
  );
}
