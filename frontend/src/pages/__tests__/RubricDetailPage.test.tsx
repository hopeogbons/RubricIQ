import { render, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { RubricDetailPage } from "@/pages/RubricDetailPage";
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
      </Routes>
    </Providers>,
  );
}

describe("RubricDetailPage", () => {
  it("renders the rubric header and the three stat numbers", async () => {
    loginAs({ role: "viewer" });
    server.use(http.get(`${API_BASE}/rubrics/${ID}`, () => HttpResponse.json(DETAIL)));
    renderApp();

    await waitFor(() => {
      expect(screen.getByTestId("rubric-display-name")).toHaveTextContent(
        "Fall 2026 Cohort A",
      );
    });
    expect(screen.getByTestId("rubric-unique-name")).toHaveTextContent(
      "fall-2026-cohort-a",
    );
    expect(screen.getByTestId("rubric-description")).toHaveTextContent(
      "A test cohort for fall 2026.",
    );
    expect(screen.getByTestId("stat-learner-count")).toHaveTextContent("12");
    expect(screen.getByTestId("stat-submission-count")).toHaveTextContent("7");
    expect(screen.getByTestId("stat-completion-rate")).toHaveTextContent("50%");
    expect(screen.getByTestId("learners-placeholder")).toBeInTheDocument();
  });

  it("shows a not-found panel on 404", async () => {
    loginAs({ role: "viewer" });
    server.use(
      http.get(`${API_BASE}/rubrics/${ID}`, () =>
        HttpResponse.json({ detail: "Rubric not found" }, { status: 404 }),
      ),
    );
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("rubric-not-found")).toBeInTheDocument();
    });
  });
});
