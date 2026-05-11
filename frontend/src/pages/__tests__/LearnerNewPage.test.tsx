import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { LearnerNewPage } from "@/pages/LearnerNewPage";
import type { Artifact } from "@/lib/artifacts";
import { API_BASE, Providers, loginAs } from "@/test/helpers";
import { server } from "@/test/msw-server";

const RUBRIC_ID = "aaaaaaaa-0000-0000-0000-000000000001";
const LEARNER_ID = "cccccccc-0000-0000-0000-000000000010";
const SUBMISSION_ID = "ssssssss-0000-0000-0000-000000000001";

interface WizardScenario {
  artifacts: Artifact[];
  /** FIFO queue of filenames the upload handler should respond with, in order. */
  uploadQueue: { type: Artifact["type"]; filename: string }[];
  evaluateResponder: () => Response;
}

function setupWizardScenario(): WizardScenario {
  const scenario: WizardScenario = {
    artifacts: [],
    uploadQueue: [],
    evaluateResponder: () =>
      HttpResponse.json(
        {
          id: SUBMISSION_ID,
          learner_id: LEARNER_ID,
          rubric_id: RUBRIC_ID,
          status: "processing",
          triggered_at: "2026-05-10T00:00:00Z",
          completed_at: null,
          error_message: null,
          created_by: null,
          created_at: "2026-05-10T00:00:00Z",
          artifacts: scenario.artifacts,
          evaluation: null,
        },
      ),
  };

  const buildSubmissionDetail = () => ({
    id: SUBMISSION_ID,
    learner_id: LEARNER_ID,
    rubric_id: RUBRIC_ID,
    status: "draft" as const,
    triggered_at: null,
    completed_at: null,
    error_message: null,
    created_by: null,
    created_at: "2026-05-10T00:00:00Z",
    artifacts: scenario.artifacts,
    evaluation: null,
  });

  server.use(
    http.post(`${API_BASE}/rubrics/${RUBRIC_ID}/learners`, () =>
      HttpResponse.json(
        {
          id: LEARNER_ID,
          rubric_id: RUBRIC_ID,
          full_name: "Ada Lovelace",
          email: null,
          cohort: null,
          created_at: "2026-05-10T00:00:00Z",
        },
        { status: 201 },
      ),
    ),
    http.post(`${API_BASE}/learners/${LEARNER_ID}/submissions`, () =>
      HttpResponse.json(buildSubmissionDetail(), { status: 201 }),
    ),
    http.get(`${API_BASE}/submissions/${SUBMISSION_ID}`, () =>
      HttpResponse.json(buildSubmissionDetail()),
    ),
    http.post(
      `${API_BASE}/submissions/${SUBMISSION_ID}/artifacts`,
      () => {
        // MSW v2 + undici cannot read FormData / text() bodies under jsdom,
        // so we don't inspect the request. Tests stage filenames via
        // scenario.uploadQueue; each upload pops one entry.
        const next = scenario.uploadQueue.shift();
        if (!next) {
          return HttpResponse.json(
            { detail: "test scenario uploadQueue was empty" },
            { status: 500 },
          );
        }
        const created: Artifact = {
          id: `art-${scenario.artifacts.length + 1}`,
          submission_id: SUBMISSION_ID,
          type: next.type,
          filename: next.filename,
          external_url: null,
          text_value: null,
          size_bytes: 0,
          created_at: "2026-05-10T00:00:00Z",
        };
        scenario.artifacts = [...scenario.artifacts, created];
        return HttpResponse.json([created], { status: 201 });
      },
    ),
    http.post(
      `${API_BASE}/submissions/${SUBMISSION_ID}/artifacts/links`,
      async ({ request }) => {
        const body = (await request.json()) as {
          links: { type: Artifact["type"]; url: string }[];
        };
        const created: Artifact[] = body.links.map((l, idx) => ({
          id: `art-link-${scenario.artifacts.length + idx + 1}`,
          submission_id: SUBMISSION_ID,
          type: l.type,
          filename: null,
          external_url: l.url,
          text_value: null,
          size_bytes: null,
          created_at: "2026-05-10T00:00:00Z",
        }));
        scenario.artifacts = [...scenario.artifacts, ...created];
        return HttpResponse.json(created, { status: 201 });
      },
    ),

    http.delete(
      `${API_BASE}/submissions/${SUBMISSION_ID}/artifacts/:artifactId`,
      ({ params }) => {
        scenario.artifacts = scenario.artifacts.filter((a) => a.id !== params.artifactId);
        return new HttpResponse(null, { status: 204 });
      },
    ),
    http.post(`${API_BASE}/submissions/${SUBMISSION_ID}/evaluate`, () =>
      scenario.evaluateResponder(),
    ),
  );

  return scenario;
}

function renderApp(path = `/rubrics/${RUBRIC_ID}/learners/new`): void {
  render(
    <Providers initialEntries={[path]}>
      <Routes>
        <Route
          path="/rubrics/:rubricId/learners/new"
          element={
            <ProtectedRoute>
              <LearnerNewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/rubrics/:id"
          element={<div data-testid="rubric-page">rubric</div>}
        />
        <Route
          path="/learners/:id"
          element={<div data-testid="learner-detail">learner detail</div>}
        />
      </Routes>
    </Providers>,
  );
}

async function completePhaseA(): Promise<void> {
  await screen.findByLabelText(/full name/i);
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/full name/i), "Ada Lovelace");
  await user.click(screen.getByTestId("phase-a-submit"));
  await waitFor(() => {
    expect(screen.getByTestId("phase-b-banner")).toBeInTheDocument();
  });
}

describe("LearnerNewPage", () => {
  it("blocks Phase A submit when full_name is empty", async () => {
    loginAs({ role: "evaluator" });
    setupWizardScenario();
    renderApp();
    await screen.findByLabelText(/full name/i);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("phase-a-submit"));
    await waitFor(() => {
      expect(screen.getByText(/full name is required/i)).toBeInTheDocument();
    });
    expect(screen.queryByTestId("phase-b-banner")).not.toBeInTheDocument();
  });

  it("surfaces a backend error from Phase A", async () => {
    loginAs({ role: "evaluator" });
    server.use(
      http.post(`${API_BASE}/rubrics/${RUBRIC_ID}/learners`, () =>
        HttpResponse.json(
          { detail: "Email already used in this rubric" },
          { status: 400 },
        ),
      ),
    );
    renderApp();
    await screen.findByLabelText(/full name/i);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/full name/i), "Ada");
    await user.click(screen.getByTestId("phase-a-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("phase-a-error")).toHaveTextContent(/already used/i);
    });
  });

  it("uploads a screenshot, adds a link, and evaluates", async () => {
    loginAs({ role: "evaluator" });
    const scenario = setupWizardScenario();
    scenario.uploadQueue.push({ type: "screenshot", filename: "shot.png" });
    renderApp();
    await completePhaseA();

    expect(screen.getByTestId("evaluate-button")).toBeDisabled();

    const user = userEvent.setup();
    const file = new File(["png-bytes"], "shot.png", { type: "image/png" });
    await user.upload(screen.getByTestId("upload-screenshot"), file);
    await waitFor(() => {
      expect(screen.getByText("shot.png")).toBeInTheDocument();
    });

    await user.type(
      screen.getByTestId("link-url"),
      "https://github.com/ada/work",
    );
    await user.click(screen.getByTestId("add-link-button"));
    await waitFor(() => {
      expect(screen.getByText("https://github.com/ada/work")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByTestId("evaluate-button")).not.toBeDisabled();
    });

    await user.click(screen.getByTestId("evaluate-button"));
    await waitFor(() => {
      expect(screen.getByTestId("learner-detail")).toBeInTheDocument();
    });
  });

  it("deletes an artifact and disables Evaluate again", async () => {
    loginAs({ role: "evaluator" });
    const scenario = setupWizardScenario();
    scenario.uploadQueue.push({ type: "screenshot", filename: "one.png" });
    renderApp();
    await completePhaseA();

    const user = userEvent.setup();
    await user.upload(
      screen.getByTestId("upload-screenshot"),
      new File(["x"], "one.png", { type: "image/png" }),
    );
    const item = await screen.findByText("one.png");
    expect(item).toBeInTheDocument();

    const deleteBtn = await screen.findByTestId("delete-artifact-art-1");
    await user.click(deleteBtn);

    await waitFor(() => {
      expect(screen.queryByText("one.png")).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("evaluate-button")).toBeDisabled();
  });

  it("surfaces a 502 from evaluate", async () => {
    loginAs({ role: "evaluator" });
    const scenario = setupWizardScenario();
    scenario.uploadQueue.push({ type: "screenshot", filename: "shot.png" });
    scenario.evaluateResponder = () =>
      HttpResponse.json(
        { detail: "Failed to reach n8n; submission left in draft" },
        { status: 502 },
      );
    renderApp();
    await completePhaseA();

    const user = userEvent.setup();
    await user.upload(
      screen.getByTestId("upload-screenshot"),
      new File(["x"], "shot.png", { type: "image/png" }),
    );
    await screen.findByText("shot.png");

    await user.click(screen.getByTestId("evaluate-button"));
    await waitFor(() => {
      expect(screen.getByTestId("evaluate-error")).toHaveTextContent(/n8n/i);
    });
    expect(screen.queryByTestId("learner-detail")).not.toBeInTheDocument();
  });
});
