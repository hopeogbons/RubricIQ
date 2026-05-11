import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminUsersPage } from "@/pages/AdminUsersPage";
import type { User } from "@/lib/auth";
import { API_BASE, Providers, loginAs } from "@/test/helpers";
import { server } from "@/test/msw-server";

function makeUser(overrides: Partial<User>): User {
  return {
    id: overrides.id ?? "00000000-0000-0000-0000-000000000000",
    email: "u@example.com",
    full_name: null,
    role: "viewer",
    is_active: true,
    activated_at: "2026-05-01T00:00:00Z",
    created_at: "2026-05-01T00:00:00Z",
    ...overrides,
  };
}

function renderApp(path = "/admin/users"): void {
  render(
    <Providers initialEntries={[path]}>
      <Routes>
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute>
              <AdminUsersPage />
            </ProtectedRoute>
          }
        />
        <Route path="/rubrics" element={<div data-testid="rubrics-list">rubrics</div>} />
      </Routes>
    </Providers>,
  );
}

const ALICE = makeUser({
  id: "11111111-1111-1111-1111-111111111111",
  email: "alice@example.com",
  full_name: "Alice Active",
  role: "evaluator",
  is_active: true,
  created_at: "2026-05-10T00:00:00Z",
});
const BOB = makeUser({
  id: "22222222-2222-2222-2222-222222222222",
  email: "bob@example.com",
  full_name: "Bob Pending",
  role: "viewer",
  is_active: false,
  activated_at: null,
  created_at: "2026-05-09T00:00:00Z",
});

function mockUsers(users: User[]): void {
  server.use(http.get(`${API_BASE}/auth/users`, () => HttpResponse.json(users)));
}

describe("AdminUsersPage", () => {
  it("redirects non-admin users to /rubrics", async () => {
    loginAs({ role: "evaluator" });
    mockUsers([ALICE, BOB]);
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("rubrics-list")).toBeInTheDocument();
    });
  });

  it("renders rows with status pills and an Activate button only for pending users", async () => {
    loginAs({ role: "admin" });
    mockUsers([ALICE, BOB]);
    renderApp();

    const aliceRow = await screen.findByTestId(`user-row-${ALICE.id}`);
    expect(within(aliceRow).getByTestId("user-status-active")).toBeInTheDocument();
    expect(within(aliceRow).queryByTestId(`activate-${ALICE.id}`)).not.toBeInTheDocument();

    const bobRow = screen.getByTestId(`user-row-${BOB.id}`);
    expect(within(bobRow).getByTestId("user-status-pending")).toBeInTheDocument();
    expect(within(bobRow).getByTestId(`activate-${BOB.id}`)).toBeInTheDocument();
  });

  it("activates a pending user, refreshes the list, and shows a success toast", async () => {
    loginAs({ role: "admin" });

    let activated = false;
    server.use(
      http.get(`${API_BASE}/auth/users`, () =>
        HttpResponse.json(
          activated
            ? [ALICE, { ...BOB, is_active: true, activated_at: "2026-05-11T00:00:00Z" }]
            : [ALICE, BOB],
        ),
      ),
      http.post(`${API_BASE}/auth/users/${BOB.id}/activate`, () => {
        activated = true;
        return HttpResponse.json({
          ...BOB,
          is_active: true,
          activated_at: "2026-05-11T00:00:00Z",
        });
      }),
    );

    renderApp();
    const user = userEvent.setup();

    const button = await screen.findByTestId(`activate-${BOB.id}`);
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByTestId("toast-success")).toHaveTextContent(/bob@example/i);
    });

    await waitFor(() => {
      const bobRow = screen.getByTestId(`user-row-${BOB.id}`);
      expect(within(bobRow).getByTestId("user-status-active")).toBeInTheDocument();
    });
    expect(screen.queryByTestId(`activate-${BOB.id}`)).not.toBeInTheDocument();
  });

  it("surfaces a destructive toast when activation fails", async () => {
    loginAs({ role: "admin" });
    mockUsers([BOB]);
    server.use(
      http.post(`${API_BASE}/auth/users/${BOB.id}/activate`, () =>
        HttpResponse.json({ detail: "User not found" }, { status: 404 }),
      ),
    );

    renderApp();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId(`activate-${BOB.id}`));

    await waitFor(() => {
      expect(screen.getByTestId("toast-destructive")).toHaveTextContent(/not found/i);
    });
  });

  it("filters rows by search input", async () => {
    loginAs({ role: "admin" });
    mockUsers([ALICE, BOB]);
    renderApp();
    await screen.findByTestId(`user-row-${ALICE.id}`);

    const user = userEvent.setup();
    await user.type(screen.getByTestId("user-search"), "bob");

    await waitFor(() => {
      expect(screen.queryByTestId(`user-row-${ALICE.id}`)).not.toBeInTheDocument();
    });
    expect(screen.getByTestId(`user-row-${BOB.id}`)).toBeInTheDocument();
  });

  it("toggles sort direction on the email column", async () => {
    loginAs({ role: "admin" });
    mockUsers([ALICE, BOB]);
    renderApp();
    await screen.findByTestId(`user-row-${ALICE.id}`);

    const user = userEvent.setup();
    await user.click(screen.getByTestId("sort-email"));

    await waitFor(() => {
      const rows = screen.getAllByTestId(/^user-row-/);
      expect(rows[0]).toHaveAttribute("data-testid", `user-row-${ALICE.id}`);
    });

    await user.click(screen.getByTestId("sort-email"));
    await waitFor(() => {
      const rows = screen.getAllByTestId(/^user-row-/);
      expect(rows[0]).toHaveAttribute("data-testid", `user-row-${BOB.id}`);
    });
  });

  it("paginates with Previous and Next disabled at boundaries", async () => {
    loginAs({ role: "admin" });
    const many = Array.from({ length: 23 }).map((_, i) =>
      makeUser({
        id: `aaaaaaaa-0000-0000-0000-${String(i).padStart(12, "0")}`,
        email: `u${i}@example.com`,
        full_name: `User ${i}`,
        created_at: `2026-05-${String((i % 28) + 1).padStart(2, "0")}T00:00:00Z`,
      }),
    );
    mockUsers(many);
    renderApp();
    await screen.findByTestId("pagination");

    const rowsPage1 = screen.getAllByTestId(/^user-row-/);
    expect(rowsPage1).toHaveLength(10);
    expect(screen.getByTestId("page-prev")).toBeDisabled();

    const user = userEvent.setup();
    await user.click(screen.getByTestId("page-next"));
    await waitFor(() => {
      expect(screen.getByTestId("pagination")).toHaveTextContent(/page 2 of 3/i);
    });
    expect(screen.getAllByTestId(/^user-row-/)).toHaveLength(10);

    await user.click(screen.getByTestId("page-next"));
    await waitFor(() => {
      expect(screen.getByTestId("pagination")).toHaveTextContent(/page 3 of 3/i);
    });
    expect(screen.getAllByTestId(/^user-row-/)).toHaveLength(3);
    expect(screen.getByTestId("page-next")).toBeDisabled();
  });
});
