import { act, render, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { AuthProvider, useAuth } from "@/lib/auth";
import { TOKEN_STORAGE_KEY } from "@/lib/api";
import { API_BASE } from "@/test/helpers";
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

function AuthProbe(): JSX.Element {
  const { status, user, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="email">{user?.email ?? ""}</span>
      <button
        type="button"
        onClick={() => {
          void login({ email: "u@example.com", password: "password123" });
        }}
      >
        login
      </button>
      <button type="button" onClick={logout}>
        logout
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  it("starts anonymous when no token is stored", async () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("anonymous");
    });
  });

  it("bootstraps the user from /auth/me when a token is present", async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, "stored-token");
    server.use(
      http.get(`${API_BASE}/auth/me`, ({ request }) => {
        expect(request.headers.get("Authorization")).toBe("Bearer stored-token");
        return HttpResponse.json(FAKE_USER);
      }),
    );
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("authenticated");
    });
    expect(screen.getByTestId("email").textContent).toBe("u@example.com");
  });

  it("clears the token on /auth/me 401", async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, "bad-token");
    server.use(
      http.get(`${API_BASE}/auth/me`, () =>
        HttpResponse.json({ detail: "expired" }, { status: 401 }),
      ),
    );
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("anonymous");
    });
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });

  it("login() stores token and transitions to authenticated", async () => {
    server.use(
      http.post(`${API_BASE}/auth/login`, () =>
        HttpResponse.json({ access_token: "new-token", token_type: "bearer" }),
      ),
      http.get(`${API_BASE}/auth/me`, ({ request }) => {
        expect(request.headers.get("Authorization")).toBe("Bearer new-token");
        return HttpResponse.json(FAKE_USER);
      }),
    );
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("anonymous");
    });
    await act(async () => {
      screen.getByText("login").click();
    });
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("authenticated");
    });
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe("new-token");
  });

  it("logout() clears the token and returns to anonymous", async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, "stored-token");
    server.use(
      http.get(`${API_BASE}/auth/me`, () => HttpResponse.json(FAKE_USER)),
    );
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("authenticated");
    });
    await act(async () => {
      screen.getByText("logout").click();
    });
    expect(screen.getByTestId("status").textContent).toBe("anonymous");
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });
});
