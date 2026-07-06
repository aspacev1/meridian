import { useAuth } from "@/lib/auth";

export function LoginPage() {
  const { login } = useAuth();

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-logo">M</div>
        <h1>Meridian</h1>
        <p>AI Data Steward — sign in to continue</p>
        <button className="btn btn-p" onClick={() => void login()}>
          Sign in with WorkOS
        </button>
      </div>
    </div>
  );
}
