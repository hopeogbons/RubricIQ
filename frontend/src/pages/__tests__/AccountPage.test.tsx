import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AccountPage } from "@/pages/AccountPage";
import { TOKEN_STORAGE_KEY } from "@/lib/api";
import { API_BASE, Providers } from "@/test/helpers";
import { server } from "@/test/msw-server";

const FAKE_USER = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "u@example.com",
  full_name: "Test User",
  role: "evaluator" as const,
  is_active: true,
  activated_at: "2026-05-01T00:00:00Z",
  created_at: "2026-05-01T00:00:00Z",
};

function renderApp(): void {
  render(
    <Providers initialEntries={["/account"]}>
      <Routes>
        <Route path="/login" element={<div data-testid="login-page">login</div>} />
        <Route
          path="/account"
          element={
            <ProtectedRoute>
              <AccountPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Providers>,
  );
}

describe("AccountPage", () => {
  it("redirects to /login when no token is present", async () => {
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("login-page")).toBeInTheDocument();
    });
  });

  it("renders the authenticated user's profile", async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, "tok");
    server.use(
      http.get(`${API_BASE}/auth/me`, () => HttpResponse.json(FAKE_USER)),
    );

    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("account-email")).toHaveTextContent("u@example.com");
    });
    expect(screen.getByTestId("account-full-name")).toHaveTextContent("Test User");
    expect(screen.getByTestId("account-role")).toHaveTextContent("evaluator");
  });

  it("logs out and redirects to /login when the logout button is clicked", async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, "tok");
    server.use(
      http.get(`${API_BASE}/auth/me`, () => HttpResponse.json(FAKE_USER)),
    );

    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("account-email")).toBeInTheDocument();
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /log out/i }));
    await waitFor(() => {
      expect(screen.getByTestId("login-page")).toBeInTheDocument();
    });
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });
});
