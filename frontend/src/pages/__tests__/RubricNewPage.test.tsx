import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { RubricNewPage } from "@/pages/RubricNewPage";
import { API_BASE, Providers, loginAs } from "@/test/helpers";
import { server } from "@/test/msw-server";

const NEW_ID = "bbbbbbbb-0000-0000-0000-000000000002";

function renderApp(path = "/rubrics/new"): void {
  render(
    <Providers initialEntries={[path]}>
      <Routes>
        <Route
          path="/rubrics/new"
          element={
            <ProtectedRoute>
              <RubricNewPage />
            </ProtectedRoute>
          }
        />
        <Route path="/rubrics" element={<div data-testid="rubrics-list">list</div>} />
        <Route
          path="/rubrics/:id"
          element={<div data-testid="rubric-detail">detail</div>}
        />
      </Routes>
    </Providers>,
  );
}

describe("RubricNewPage", () => {
  it("creates a rubric and redirects to its detail page", async () => {
    loginAs({ role: "admin" });
    server.use(
      http.post(`${API_BASE}/rubrics`, async ({ request }) => {
        const body = (await request.json()) as { unique_name: string; display_name: string };
        expect(body.unique_name).toBe("fall-2026");
        expect(body.display_name).toBe("Fall 2026");
        return HttpResponse.json(
          {
            id: NEW_ID,
            unique_name: body.unique_name,
            display_name: body.display_name,
            description: null,
            google_sheet_id: null,
            google_drive_folder_path: null,
            created_by: null,
            created_at: "2026-05-10T00:00:00Z",
          },
          { status: 201 },
        );
      }),
    );

    renderApp();
    await screen.findByLabelText(/unique name/i);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/unique name/i), "fall-2026");
    await user.type(screen.getByLabelText(/display name/i), "Fall 2026");
    await user.click(screen.getByRole("button", { name: /create rubric/i }));

    await waitFor(() => {
      expect(screen.getByTestId("rubric-detail")).toBeInTheDocument();
    });
  });

  it("surfaces a duplicate-name error from the backend", async () => {
    loginAs({ role: "admin" });
    server.use(
      http.post(`${API_BASE}/rubrics`, () =>
        HttpResponse.json(
          { detail: "A rubric with that unique_name already exists" },
          { status: 400 },
        ),
      ),
    );

    renderApp();
    await screen.findByLabelText(/unique name/i);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/unique name/i), "taken");
    await user.type(screen.getByLabelText(/display name/i), "Taken");
    await user.click(screen.getByRole("button", { name: /create rubric/i }));

    await waitFor(() => {
      expect(screen.getByTestId("rubric-new-error")).toHaveTextContent(/already exists/i);
    });
  });

  it("rejects an invalid unique_name client-side before calling the API", async () => {
    loginAs({ role: "admin" });
    renderApp();
    await screen.findByLabelText(/unique name/i);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/unique name/i), "Has Spaces");
    await user.type(screen.getByLabelText(/display name/i), "Bad");
    await user.click(screen.getByRole("button", { name: /create rubric/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/lowercase letters, digits, and hyphens only/i),
      ).toBeInTheDocument();
    });
  });

  it("redirects non-admin users to /rubrics", async () => {
    loginAs({ role: "viewer" });
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId("rubrics-list")).toBeInTheDocument();
    });
  });
});
