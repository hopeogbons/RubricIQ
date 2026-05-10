import { render, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { DashboardPage } from "@/pages/DashboardPage";
import { API_BASE, Providers, loginAs } from "@/test/helpers";
import { server } from "@/test/msw-server";

const STATS = {
  total_rubrics: 3,
  total_learners: 17,
  total_submissions: 25,
  completion_rate: 0.64,
};

const RUBRICS = [
  {
    id: "aaaaaaaa-0000-0000-0000-000000000001",
    unique_name: "fall-2026",
    display_name: "Fall 2026",
    description: null,
    google_sheet_id: null,
    google_drive_folder_path: null,
    created_by: null,
    created_at: "2026-05-01T12:00:00Z",
  },
];

function renderApp(path = "/dashboard"): void {
  render(
    <Providers initialEntries={[path]}>
      <Routes>
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route path="/rubrics" element={<div data-testid="rubrics-list">rubrics</div>} />
        <Route
          path="/rubrics/:id"
          element={<div data-testid="rubric-detail">detail</div>}
        />
      </Routes>
    </Providers>,
  );
}

describe("DashboardPage", () => {
  it("renders global stats and the rubric list for an admin", async () => {
    loginAs({ role: "admin" });
    server.use(
      http.get(`${API_BASE}/dashboard/stats`, () => HttpResponse.json(STATS)),
      http.get(`${API_BASE}/rubrics`, () => HttpResponse.json(RUBRICS)),
    );
    renderApp();

    await waitFor(() => {
      expect(screen.getByTestId("stat-total-rubrics")).toHaveTextContent("3");
    });
    expect(screen.getByTestId("stat-total-learners")).toHaveTextContent("17");
    expect(screen.getByTestId("stat-total-submissions")).toHaveTextContent("25");
    expect(screen.getByTestId("stat-overall-completion")).toHaveTextContent("64%");
    expect(
      await screen.findByTestId(`dashboard-rubric-${RUBRICS[0]!.id}`),
    ).toHaveTextContent("Fall 2026");
  });

  it("renders empty state when there are no rubrics", async () => {
    loginAs({ role: "superadmin" });
    server.use(
      http.get(`${API_BASE}/dashboard/stats`, () =>
        HttpResponse.json({
          total_rubrics: 0,
          total_learners: 0,
          total_submissions: 0,
          completion_rate: 0,
        }),
      ),
      http.get(`${API_BASE}/rubrics`, () => HttpResponse.json([])),
    );
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("dashboard-rubrics-empty")).toBeInTheDocument();
    });
  });

  it("redirects non-admin users to /rubrics", async () => {
    loginAs({ role: "evaluator" });
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("rubrics-list")).toBeInTheDocument();
    });
  });

  it("surfaces a stats load failure", async () => {
    loginAs({ role: "admin" });
    server.use(
      http.get(`${API_BASE}/dashboard/stats`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
      http.get(`${API_BASE}/rubrics`, () => HttpResponse.json([])),
    );
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("dashboard-stats-error")).toHaveTextContent(/boom/i);
    });
  });
});
