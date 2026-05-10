import { Navigate, Route, Routes } from "react-router-dom";

import { NavBar } from "@/components/NavBar";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AccountPage } from "@/pages/AccountPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LearnerDetailPage } from "@/pages/LearnerDetailPage";
import { LearnerNewPage } from "@/pages/LearnerNewPage";
import { LoginPage } from "@/pages/LoginPage";
import { RubricDetailPage } from "@/pages/RubricDetailPage";
import { RubricNewPage } from "@/pages/RubricNewPage";
import { RubricsListPage } from "@/pages/RubricsListPage";
import { SignupPage } from "@/pages/SignupPage";

export function App(): JSX.Element {
  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/rubrics" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            path="/rubrics"
            element={
              <ProtectedRoute>
                <RubricsListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/rubrics/new"
            element={
              <ProtectedRoute>
                <RubricNewPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/rubrics/:id"
            element={
              <ProtectedRoute>
                <RubricDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/rubrics/:rubricId/learners/new"
            element={
              <ProtectedRoute>
                <LearnerNewPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/learners/:id"
            element={
              <ProtectedRoute>
                <LearnerDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/account"
            element={
              <ProtectedRoute>
                <AccountPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/rubrics" replace />} />
        </Routes>
      </main>
    </div>
  );
}
