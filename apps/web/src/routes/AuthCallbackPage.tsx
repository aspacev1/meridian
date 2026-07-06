import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export function AuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const { completeLogin } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError("Missing authorization code from WorkOS redirect.");
      return;
    }
    if (started.current) return;
    started.current = true;

    completeLogin(code)
      .then((me) => {
        navigate(me.memberships.length > 0 ? "/dashboard" : "/no-org", { replace: true });
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.detail : "Sign-in failed.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return (
    <div className="auth-screen">
      <div className="auth-card">
        {error ? (
          <>
            <h1>Sign-in failed</h1>
            <p>{error}</p>
          </>
        ) : (
          <p>Completing sign-in…</p>
        )}
      </div>
    </div>
  );
}
