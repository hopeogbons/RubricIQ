import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { RubricDetailPage } from "@/pages/RubricDetailPage";
import type { Learner } from "@/lib/learners";
import { API_BASE, Providers, loginAs } from "@/test/helpers";
import { server } from "@/test/msw-server";

const ID = "aaaaaaaa-0000-0000-0000-000000000001";
const DETAIL = {
  id: ID,
  unique_name: "fall-2026-cohort-a",
  display_name: "Fall 2026 Cohort A",
  description: "A test cohort for fall 2026.",
  google_sheet_id: null,
  google_drive_folder_path: null,
  created_by: null,
  created_at: "2026-05-01T12:00:00Z",
  learner_count: 12,
  submission_count: 7,
  completion_rate: 0.5,
};

const LEARNER: Learner = {
  id: "cccccccc-0000-0000-0000-000000000010",
  rubric_id: ID,
  full_name: "Ada Lovelace",
  email: "ada@example.com",
  cohort: "Spring 2026",
  created_at: "2026-05-02T00:00:00Z",
};

function mockRubric(): void {
  server.use(http.get(`${API_BASE}/rubrics/${ID}`, () => HttpResponse.json(DETAIL)));
}

function mockLearners(learners: Learner[]): void {
  server.use(
    http.get(`${API_BASE}/rubrics/${ID}/learners`, () => HttpResponse.json(learners)),
  );
}

function renderApp(path = `/rubrics/${ID}`): void {
  render(
    <Providers initialEntries={[path]}>
      <Routes>
        <Route
          path="/rubrics/:id"
          element={
            <ProtectedRoute>
              <RubricDetailPage />
            </ProtectedRoute>
          }
        />
        <Route path="/rubrics" element={<div data-testid="rubrics-list">list</div>} />
        <Route
          path="/rubrics/:rubricId/learners/new"
          element={<div data-testid="learner-new">new learner</div>}
        />
        <Route
          path="/learners/:id"
          element={<div data-testid="learner-detail">learner detail</div>}
        />
      </Routes>
    </Providers>,
  );
}

describe("RubricDetailPage", () => {
  it("renders the rubric header, three stat numbers, and learners empty state", async () => {
    loginAs({ role: "viewer" });
    mockRubric();
    mockLearners([]);

    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("rubric-display-name")).toHaveTextContent(
        "Fall 2026 Cohort A",
      );
    });
    expect(screen.getByTestId("stat-completion-rate")).toHaveTextContent("50%");
    await waitFor(() => {
      expect(screen.getByTestId("learners-empty")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("add-learner-button")).not.toBeInTheDocument();
  });

  it("renders the learners table and navigates to the learner on click", async () => {
    loginAs({ role: "evaluator" });
    mockRubric();
    mockLearners([LEARNER]);

    renderApp();
    const row = await screen.findByTestId(`learner-row-${LEARNER.id}`);
    expect(row).toHaveTextContent("Ada Lovelace");
    expect(row).toHaveTextContent("ada@example.com");
    expect(row).toHaveTextContent("Spring 2026");

    await userEvent.setup().click(row);
    await waitFor(() => {
      expect(screen.getByTestId("learner-detail")).toBeInTheDocument();
    });
  });

  it("shows Add learner for admin and evaluator, hides it for viewer", async () => {
    loginAs({ role: "admin" });
    mockRubric();
    mockLearners([]);

    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("add-learner-button")).toBeInTheDocument();
    });
  });

  it("shows a not-found panel on 404", async () => {
    loginAs({ role: "viewer" });
    server.use(
      http.get(`${API_BASE}/rubrics/${ID}`, () =>
        HttpResponse.json({ detail: "Rubric not found" }, { status: 404 }),
      ),
      http.get(`${API_BASE}/rubrics/${ID}/learners`, () => HttpResponse.json([])),
    );
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("rubric-not-found")).toBeInTheDocument();
    });
  });
});
