import { useAuth } from "@/lib/auth";

export function NoOrgPage() {
  const { logout } = useAuth();

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h1>No organization yet</h1>
        <p>Your account isn't a member of any Meridian organization yet.</p>
        <button className="btn btn-s" onClick={logout}>
          Sign out
        </button>
      </div>
    </div>
  );
}
