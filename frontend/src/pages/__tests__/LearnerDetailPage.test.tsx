import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { LearnerDetailPage } from "@/pages/LearnerDetailPage";
import { API_BASE, Providers, loginAs } from "@/test/helpers";
import { server } from "@/test/msw-server";

const LEARNER_ID = "cccccccc-0000-0000-0000-000000000010";
const RUBRIC_ID = "aaaaaaaa-0000-0000-0000-000000000001";
const SUBMISSION_ID = "ssssssss-0000-0000-0000-000000000001";

const LEARNER_BASE = {
  id: LEARNER_ID,
  rubric_id: RUBRIC_ID,
  full_name: "Ada Lovelace",
  email: "ada@example.com",
  cohort: "Spring 2026",
  created_at: "2026-05-02T00:00:00Z",
};

function submissionSummary(overrides: Record<string, unknown> = {}) {
  return {
    id: SUBMISSION_ID,
    status: "complete",
    triggered_at: "2026-05-03T00:00:00Z",
    completed_at: "2026-05-03T00:05:00Z",
    error_message: null,
    created_at: "2026-05-03T00:00:00Z",
    total_score: 38,
    max_total: 50,
    evaluated_at: "2026-05-03T00:05:00Z",
    ...overrides,
  };
}

function submissionDetail(overrides: Record<string, unknown> = {}) {
  return {
    id: SUBMISSION_ID,
    learner_id: LEARNER_ID,
    rubric_id: RUBRIC_ID,
    status: "complete",
    triggered_at: "2026-05-03T00:00:00Z",
    completed_at: "2026-05-03T00:05:00Z",
    error_message: null,
    created_by: null,
    created_at: "2026-05-03T00:00:00Z",
    artifacts: [],
    evaluation: {
      id: "eval-1",
      submission_id: SUBMISSION_ID,
      total_score: 38,
      max_total: 50,
      evaluated_at: "2026-05-03T00:05:00Z",
      scores: [
        {
          id: "score-1",
          criterion: "Code quality",
          score: 4,
          max_score: 5,
          explanation: "Clean.",
        },
      ],
    },
    ...overrides,
  };
}

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
        <Route
          path="/rubrics/:rubricId/learners/new"
          element={<div data-testid="learner-new">learner new</div>}
        />
      </Routes>
    </Providers>,
  );
}

describe("LearnerDetailPage", () => {
  it("renders header, the single submission, and per-criterion scores", async () => {
    loginAs({ role: "evaluator" });
    server.use(
      http.get(`${API_BASE}/learners/${LEARNER_ID}`, () =>
        HttpResponse.json({
          ...LEARNER_BASE,
          submissions: [submissionSummary()],
        }),
      ),
      http.get(`${API_BASE}/submissions/${SUBMISSION_ID}`, () =>
        HttpResponse.json(submissionDetail()),
      ),
    );
    renderApp();

    await waitFor(() => {
      expect(screen.getByTestId("learner-full-name")).toHaveTextContent(
        "Ada Lovelace",
      );
    });
    const summary = await screen.findByTestId("submission-summary");
    expect(summary).toHaveTextContent(/complete/i);
    expect(screen.getByTestId("submission-score")).toHaveTextContent("38 / 50");
    expect(screen.getByTestId("scores-card")).toBeInTheDocument();
    expect(screen.getByTestId("score-row-score-1")).toHaveTextContent(
      "Code quality",
    );
  });

  it("renders the no-submission state when the learner has none yet", async () => {
    loginAs({ role: "evaluator" });
    server.use(
      http.get(`${API_BASE}/learners/${LEARNER_ID}`, () =>
        HttpResponse.json({ ...LEARNER_BASE, submissions: [] }),
      ),
    );
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("no-submission")).toBeInTheDocument();
    });
  });

  it("shows a failure alert and a Re-evaluate button on a failed submission", async () => {
    loginAs({ role: "evaluator" });
    server.use(
      http.get(`${API_BASE}/learners/${LEARNER_ID}`, () =>
        HttpResponse.json({
          ...LEARNER_BASE,
          submissions: [
            submissionSummary({
              status: "failed",
              error_message: "n8n timed out",
              total_score: null,
              max_total: null,
              evaluated_at: null,
            }),
          ],
        }),
      ),
      http.get(`${API_BASE}/submissions/${SUBMISSION_ID}`, () =>
        HttpResponse.json(
          submissionDetail({
            status: "failed",
            error_message: "n8n timed out",
            evaluation: null,
            artifacts: [
              {
                id: "art-1",
                submission_id: SUBMISSION_ID,
                type: "github",
                filename: null,
                external_url: "https://github.com/ada/work",
                text_value: null,
                size_bytes: null,
                created_at: "2026-05-02T00:00:00Z",
              },
            ],
          }),
        ),
      ),
    );
    renderApp();

    expect(await screen.findByTestId("submission-failure")).toHaveTextContent(
      /timed out/i,
    );
    // Re-evaluate is enabled when artifacts exist and status is not processing.
    const btn = screen.getByTestId("evaluate-button");
    expect(btn).toHaveTextContent(/re-evaluate/i);
    expect(btn).not.toBeDisabled();
  });

  it("re-evaluates and shows a success toast on a completed submission", async () => {
    loginAs({ role: "evaluator" });
    server.use(
      http.get(`${API_BASE}/learners/${LEARNER_ID}`, () =>
        HttpResponse.json({
          ...LEARNER_BASE,
          submissions: [submissionSummary()],
        }),
      ),
      http.get(`${API_BASE}/submissions/${SUBMISSION_ID}`, () =>
        HttpResponse.json(
          submissionDetail({
            artifacts: [
              {
                id: "art-1",
                submission_id: SUBMISSION_ID,
                type: "github",
                filename: null,
                external_url: "https://github.com/ada/work",
                text_value: null,
                size_bytes: null,
                created_at: "2026-05-02T00:00:00Z",
              },
            ],
          }),
        ),
      ),
      http.post(`${API_BASE}/submissions/${SUBMISSION_ID}/evaluate`, () =>
        HttpResponse.json(
          submissionDetail({ status: "processing", evaluation: null }),
        ),
      ),
    );
    renderApp();

    const btn = await screen.findByTestId("evaluate-button");
    expect(btn).toHaveTextContent(/re-evaluate/i);
    await userEvent.setup().click(btn);

    await waitFor(() => {
      expect(screen.getByTestId("toast-success")).toHaveTextContent(
        /re-evaluation started/i,
      );
    });
  });

  it("locks the artifact panel while a submission is processing", async () => {
    loginAs({ role: "evaluator" });
    server.use(
      http.get(`${API_BASE}/learners/${LEARNER_ID}`, () =>
        HttpResponse.json({
          ...LEARNER_BASE,
          submissions: [submissionSummary({ status: "processing" })],
        }),
      ),
      http.get(`${API_BASE}/submissions/${SUBMISSION_ID}`, () =>
        HttpResponse.json(
          submissionDetail({
            status: "processing",
            evaluation: null,
            artifacts: [],
          }),
        ),
      ),
    );
    renderApp();

    await waitFor(() => {
      expect(screen.getByTestId("artifacts-readonly")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("artifact-panel")).not.toBeInTheDocument();
    expect(screen.getByTestId("evaluate-button")).toBeDisabled();
  });

  it("shows a not-found panel on 404", async () => {
    loginAs({ role: "evaluator" });
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
