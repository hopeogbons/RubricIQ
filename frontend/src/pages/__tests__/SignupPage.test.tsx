import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { SignupPage } from "@/pages/SignupPage";
import { TOKEN_STORAGE_KEY } from "@/lib/api";
import { API_BASE, Providers } from "@/test/helpers";
import { server } from "@/test/msw-server";

function renderSignup(): void {
  render(
    <Providers initialEntries={["/signup"]}>
      <SignupPage />
    </Providers>,
  );
}

describe("SignupPage", () => {
  it("creates an account and shows the pending-activation panel", async () => {
    server.use(
      http.post(`${API_BASE}/auth/signup`, async ({ request }) => {
        const body = (await request.json()) as { email: string; password: string };
        expect(body.email).toBe("new@example.com");
        expect(body.password).toBe("password123");
        return HttpResponse.json(
          {
            id: "22222222-2222-2222-2222-222222222222",
            email: body.email,
            full_name: null,
            role: "viewer",
            is_active: false,
            activated_at: null,
            created_at: "2026-05-10T00:00:00Z",
          },
          { status: 201 },
        );
      }),
    );

    renderSignup();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), "new@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByTestId("signup-success")).toBeInTheDocument();
    });
    expect(screen.getByTestId("signup-success")).toHaveTextContent("new@example.com");
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });

  it("surfaces a duplicate-email error from the backend", async () => {
    server.use(
      http.post(`${API_BASE}/auth/signup`, () =>
        HttpResponse.json({ detail: "Email already registered" }, { status: 409 }),
      ),
    );

    renderSignup();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), "dupe@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByTestId("signup-error")).toHaveTextContent(/already registered/i);
    });
    expect(screen.queryByTestId("signup-success")).not.toBeInTheDocument();
  });

  it("rejects passwords shorter than 8 characters before calling the API", async () => {
    renderSignup();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), "ok@example.com");
    await user.type(screen.getByLabelText(/password/i), "short");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    });
  });
});
