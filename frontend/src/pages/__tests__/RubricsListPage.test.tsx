import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { RubricsListPage } from "@/pages/RubricsListPage";
import { API_BASE, Providers, loginAs } from "@/test/helpers";
import { server } from "@/test/msw-server";

const RUBRICS = [
  {
    id: "aaaaaaaa-0000-0000-0000-000000000001",
    unique_name: "fall-2026-cohort-a",
    display_name: "Fall 2026 Cohort A",
    description: null,
    google_sheet_id: null,
    google_drive_folder_path: null,
    created_by: null,
    created_at: "2026-05-01T12:00:00Z",
  },
];

function renderApp(initialPath = "/rubrics"): void {
  render(
    <Providers initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="/rubrics"
          element={
            <ProtectedRoute>
              <RubricsListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/rubrics/:id"
          element={<div data-testid="rubric-detail">detail</div>}
        />
        <Route path="/rubrics/new" element={<div data-testid="rubric-new">new</div>} />
      </Routes>
    </Providers>,
  );
}

describe("RubricsListPage", () => {
  it("renders the empty state when the user has no rubrics", async () => {
    loginAs({ role: "viewer" });
    server.use(http.get(`${API_BASE}/rubrics`, () => HttpResponse.json([])));
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("rubrics-empty")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("new-rubric-button")).not.toBeInTheDocument();
  });

  it("renders rows and navigates to detail when one is clicked", async () => {
    loginAs({ role: "viewer" });
    server.use(http.get(`${API_BASE}/rubrics`, () => HttpResponse.json(RUBRICS)));
    renderApp();
    const row = await screen.findByTestId(`rubric-row-${RUBRICS[0]!.id}`);
    expect(row).toHaveTextContent("Fall 2026 Cohort A");
    expect(row).toHaveTextContent("fall-2026-cohort-a");

    await userEvent.setup().click(row);
    await waitFor(() => {
      expect(screen.getByTestId("rubric-detail")).toBeInTheDocument();
    });
  });

  it("shows the New rubric button only for admin and superadmin", async () => {
    loginAs({ role: "admin" });
    server.use(http.get(`${API_BASE}/rubrics`, () => HttpResponse.json([])));
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("new-rubric-button")).toBeInTheDocument();
    });
  });

  it("surfaces a load failure", async () => {
    loginAs({ role: "viewer" });
    server.use(
      http.get(`${API_BASE}/rubrics`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("rubrics-error")).toHaveTextContent(/boom/i);
    });
  });
});
