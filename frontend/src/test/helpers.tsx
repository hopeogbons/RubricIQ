import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HttpResponse, http } from "msw";
import { MemoryRouter } from "react-router-dom";

import { TOKEN_STORAGE_KEY } from "@/lib/api";
import { AuthProvider, type User } from "@/lib/auth";
import { ToastProvider, Toaster } from "@/lib/toast";
import { server } from "@/test/msw-server";

interface ProvidersProps {
  children: ReactNode;
  initialEntries?: string[];
}

export function Providers({ children, initialEntries = ["/"] }: ProvidersProps): JSX.Element {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        <ToastProvider durationMs={60_000}>
          <AuthProvider>
            {children}
            <Toaster />
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

export const API_BASE = "http://localhost:8000";

const DEFAULT_USER: User = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "u@example.com",
  full_name: null,
  role: "viewer",
  is_active: true,
  activated_at: "2026-05-01T00:00:00Z",
  created_at: "2026-05-01T00:00:00Z",
};

/** Seed a token and an /auth/me MSW handler so AuthProvider boots to `authenticated`. */
export function loginAs(overrides: Partial<User> = {}): User {
  const user: User = { ...DEFAULT_USER, ...overrides };
  window.localStorage.setItem(TOKEN_STORAGE_KEY, "test-token");
  server.use(http.get(`${API_BASE}/auth/me`, () => HttpResponse.json(user)));
  return user;
}
