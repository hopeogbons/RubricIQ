import { render, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { LearnerDetailPage } from "@/pages/LearnerDetailPage";
import { API_BASE, Providers, loginAs } from "@/test/helpers";
import { server } from "@/test/msw-server";

const LEARNER_ID = "cccccccc-0000-0000-0000-000000000010";
const RUBRIC_ID = "aaaaaaaa-0000-0000-0000-000000000001";

const DETAIL = {
  id: LEARNER_ID,
  rubric_id: RUBRIC_ID,
  full_name: "Ada Lovelace",
  email: "ada@example.com",
  cohort: "Spring 2026",
  created_at: "2026-05-02T00:00:00Z",
  submissions: [
    {
      id: "ssssssss-0000-0000-0000-000000000001",
      status: "complete" as const,
      triggered_at: "2026-05-03T00:00:00Z",
      completed_at: "2026-05-03T00:05:00Z",
      error_message: null,
      created_at: "2026-05-03T00:00:00Z",
      total_score: 38,
      max_total: 50,
      evaluated_at: "2026-05-03T00:05:00Z",
    },
    {
      id: "ssssssss-0000-0000-0000-000000000002",
      status: "failed" as const,
      triggered_at: "2026-05-04T00:00:00Z",
      completed_at: "2026-05-04T00:30:00Z",
      error_message: "n8n timed out",
      created_at: "2026-05-04T00:00:00Z",
      total_score: null,
      max_total: null,
      evaluated_at: null,
    },
  ],
};

function renderApp(path = `/learners/${LEARNER_ID}`): void {
  render(
    <Providers initialEntries={[path]}>
      <Routes>
        <Route
          path="/learners/:id"
          element={
            <ProtectedRoute>
              <LearnerDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/rubrics/:id"
          element={<div data-testid="rubric-page">rubric</div>}
        />
      </Routes>
    </Providers>,
  );
}

describe("LearnerDetailPage", () => {
  it("renders header, email, cohort, and submission rows", async () => {
    loginAs({ role: "viewer" });
    server.use(
      http.get(`${API_BASE}/learners/${LEARNER_ID}`, () => HttpResponse.json(DETAIL)),
    );
    renderApp();

    await waitFor(() => {
      expect(screen.getByTestId("learner-full-name")).toHaveTextContent(
        "Ada Lovelace",
      );
    });
    expect(screen.getByTestId("learner-email")).toHaveTextContent("ada@example.com");
    expect(screen.getByTestId("learner-cohort")).toHaveTextContent("Spring 2026");

    const completeRow = screen.getByTestId(
      "submission-row-ssssssss-0000-0000-0000-000000000001",
    );
    expect(completeRow).toHaveTextContent("complete");
    expect(
      screen.getByTestId("submission-score-ssssssss-0000-0000-0000-000000000001"),
    ).toHaveTextContent("38 / 50");

    const failedRow = screen.getByTestId(
      "submission-row-ssssssss-0000-0000-0000-000000000002",
    );
    expect(failedRow).toHaveTextContent("failed");
    expect(failedRow).toHaveTextContent("n8n timed out");
    expect(
      screen.getByTestId("submission-score-ssssssss-0000-0000-0000-000000000002"),
    ).toHaveTextContent("-");
  });

  it("renders an empty state when the learner has no submissions", async () => {
    loginAs({ role: "viewer" });
    server.use(
      http.get(`${API_BASE}/learners/${LEARNER_ID}`, () =>
        HttpResponse.json({ ...DETAIL, submissions: [] }),
      ),
    );
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("submissions-empty")).toBeInTheDocument();
    });
  });

  it("shows a not-found panel on 404", async () => {
    loginAs({ role: "viewer" });
    server.use(
      http.get(`${API_BASE}/learners/${LEARNER_ID}`, () =>
        HttpResponse.json({ detail: "Learner not found" }, { status: 404 }),
      ),
    );
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("learner-not-found")).toBeInTheDocument();
    });
  });
});
