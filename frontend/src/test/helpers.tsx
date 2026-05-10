import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { AuthProvider } from "@/lib/auth";

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
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

export const API_BASE = "http://localhost:8000";
