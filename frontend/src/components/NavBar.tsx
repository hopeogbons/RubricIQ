import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

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
        <Link to="/" className="font-semibold">
          RubricIQ
        </Link>
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
