import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { AppShell } from "@/components/AppShell";
import { LoginPage } from "@/routes/LoginPage";
import { AuthCallbackPage } from "@/routes/AuthCallbackPage";
import { NoOrgPage } from "@/routes/NoOrgPage";
import { DashboardPage } from "@/routes/DashboardPage";
import { CatalogPage } from "@/routes/CatalogPage";
import { PlaceholderPage } from "@/routes/PlaceholderPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuth();
  if (isLoading) return <div className="state-message">Loading…</div>;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/no-org" element={<NoOrgPage />} />

      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route
          path="/tasks"
          element={
            <PlaceholderPage
              title="Task Board"
              note="Coming in a later phase — needs the AI task-generation and persistence backend."
            />
          }
        />
        <Route
          path="/chat"
          element={
            <PlaceholderPage
              title="Chat"
              note="Coming in a later phase — needs the real Claude-backed chat backend."
            />
          }
        />
        <Route
          path="/settings"
          element={
            <PlaceholderPage
              title="Settings"
              note="Coming in a later phase — mart registration and connector management."
            />
          }
        />
        <Route
          path="/executive"
          element={
            <PlaceholderPage
              title="Executive View"
              note="Coming in a later phase — needs historical scan-data aggregation."
            />
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
