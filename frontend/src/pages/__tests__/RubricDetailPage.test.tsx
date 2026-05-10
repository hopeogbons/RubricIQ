import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { RubricDetailPage } from "@/pages/RubricDetailPage";
import type { RubricChartStats } from "@/lib/dashboard";
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

const EMPTY_CHART_STATS: RubricChartStats = {
  rubric_id: ID,
  average_total_score: null,
  average_max_total: null,
  score_distribution: [
    { bucket: "0-10%", count: 0 },
    { bucket: "10-20%", count: 0 },
    { bucket: "20-30%", count: 0 },
    { bucket: "30-40%", count: 0 },
    { bucket: "40-50%", count: 0 },
    { bucket: "50-60%", count: 0 },
    { bucket: "60-70%", count: 0 },
    { bucket: "70-80%", count: 0 },
    { bucket: "80-90%", count: 0 },
    { bucket: "90-100%", count: 0 },
  ],
  criterion_averages: [],
};

function mockChartStats(stats: RubricChartStats = EMPTY_CHART_STATS): void {
  server.use(
    http.get(`${API_BASE}/dashboard/rubrics/${ID}/stats`, () =>
      HttpResponse.json(stats),
    ),
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
    mockChartStats();

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
    await waitFor(() => {
      expect(screen.getByTestId("score-histogram-empty")).toBeInTheDocument();
    });
    expect(screen.getByTestId("criterion-averages-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("add-learner-button")).not.toBeInTheDocument();
  });

  it("renders the learners table and navigates to the learner on click", async () => {
    loginAs({ role: "evaluator" });
    mockRubric();
    mockLearners([LEARNER]);
    mockChartStats();

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
    mockChartStats();

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
      http.get(`${API_BASE}/dashboard/rubrics/${ID}/stats`, () =>
        HttpResponse.json(EMPTY_CHART_STATS),
      ),
    );
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("rubric-not-found")).toBeInTheDocument();
    });
  });

  it("renders charts and average score when stats arrive", async () => {
    loginAs({ role: "admin" });
    mockRubric();
    mockLearners([]);
    mockChartStats({
      rubric_id: ID,
      average_total_score: 8,
      average_max_total: 10,
      score_distribution: [
        { bucket: "0-10%", count: 0 },
        { bucket: "10-20%", count: 0 },
        { bucket: "20-30%", count: 1 },
        { bucket: "30-40%", count: 0 },
        { bucket: "40-50%", count: 0 },
        { bucket: "50-60%", count: 0 },
        { bucket: "60-70%", count: 0 },
        { bucket: "70-80%", count: 2 },
        { bucket: "80-90%", count: 1 },
        { bucket: "90-100%", count: 0 },
      ],
      criterion_averages: [
        { criterion: "Clarity", average: 4, max_score_average: 5, count: 4 },
        { criterion: "Depth", average: 3, max_score_average: 5, count: 4 },
      ],
    });
    renderApp();

    await waitFor(() => {
      expect(screen.getByTestId("stat-average-total")).toHaveTextContent("8 / 10");
    });
    expect(await screen.findByTestId("score-histogram")).toBeInTheDocument();
    expect(screen.getByTestId("criterion-averages-chart")).toBeInTheDocument();
    expect(screen.queryByTestId("score-histogram-empty")).not.toBeInTheDocument();
    expect(screen.queryByTestId("criterion-averages-empty")).not.toBeInTheDocument();
  });
});
