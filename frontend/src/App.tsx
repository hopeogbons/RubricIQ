import { Navigate, Route, Routes } from "react-router-dom";

import { NavBar } from "@/components/NavBar";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AccountPage } from "@/pages/AccountPage";
import { LoginPage } from "@/pages/LoginPage";
import { SignupPage } from "@/pages/SignupPage";

export function App(): JSX.Element {
  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/account" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            path="/account"
            element={
              <ProtectedRoute>
                <AccountPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/account" replace />} />
        </Routes>
      </main>
    </div>
  );
}
