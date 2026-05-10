import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { LoginPage } from "@/pages/LoginPage";
import { TOKEN_STORAGE_KEY } from "@/lib/api";
import { API_BASE, Providers } from "@/test/helpers";
import { server } from "@/test/msw-server";

const FAKE_USER = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "u@example.com",
  full_name: null,
  role: "viewer" as const,
  is_active: true,
  activated_at: "2026-05-01T00:00:00Z",
  created_at: "2026-05-01T00:00:00Z",
};

function renderLogin(): void {
  render(
    <Providers initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/account" element={<div data-testid="account-page">account</div>} />
      </Routes>
    </Providers>,
  );
}

describe("LoginPage", () => {
  it("logs in and redirects to /account on success", async () => {
    server.use(
      http.post(`${API_BASE}/auth/login`, async ({ request }) => {
        const body = (await request.json()) as { email: string; password: string };
        expect(body.email).toBe("u@example.com");
        expect(body.password).toBe("password123");
        return HttpResponse.json({ access_token: "tok", token_type: "bearer" });
      }),
      http.get(`${API_BASE}/auth/me`, () => HttpResponse.json(FAKE_USER)),
    );

    renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), "u@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByTestId("account-page")).toBeInTheDocument();
    });
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe("tok");
  });

  it("shows an error on invalid credentials and does not store a token", async () => {
    server.use(
      http.post(`${API_BASE}/auth/login`, () =>
        HttpResponse.json({ detail: "Invalid email or password" }, { status: 401 }),
      ),
    );

    renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), "u@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByTestId("login-error")).toHaveTextContent(
        /invalid email or password/i,
      );
    });
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(screen.queryByTestId("account-page")).not.toBeInTheDocument();
  });

  it("surfaces the inactive-account error from the backend", async () => {
    server.use(
      http.post(`${API_BASE}/auth/login`, () =>
        HttpResponse.json({ detail: "Account is not active" }, { status: 403 }),
      ),
    );

    renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), "pending@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByTestId("login-error")).toHaveTextContent(/not active/i);
    });
  });
});
