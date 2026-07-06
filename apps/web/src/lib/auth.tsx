import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiFetch } from "./api";
import type { Me } from "./types";

const TOKEN_KEY = "meridian_access_token";
const ORG_KEY = "meridian_current_org_id";

interface AuthContextValue {
  token: string | null;
  me: Me | null;
  currentOrgId: string | null;
  isLoading: boolean;
  setCurrentOrgId: (orgId: string) => void;
  login: () => Promise<void>;
  logout: () => void;
  /** Exchanges a WorkOS authorization code for tokens, then loads /auth/me. */
  completeLogin: (code: string) => Promise<Me>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [me, setMe] = useState<Me | null>(null);
  const [currentOrgId, setCurrentOrgIdState] = useState<string | null>(() =>
    localStorage.getItem(ORG_KEY),
  );
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }
    apiFetch<Me>("/auth/me", { token })
      .then((result) => {
        setMe(result);
        if (!currentOrgId && result.memberships.length > 0) {
          setCurrentOrgId(result.memberships[0].org_id);
        }
      })
      .catch(() => {
        // token expired/invalid -- drop it and force a re-login
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
      })
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  function setCurrentOrgId(orgId: string) {
    localStorage.setItem(ORG_KEY, orgId);
    setCurrentOrgIdState(orgId);
  }

  async function login() {
    const { url } = await apiFetch<{ url: string }>("/auth/login-url");
    window.location.href = url;
  }

  async function completeLogin(code: string): Promise<Me> {
    const tokens = await apiFetch<{ access_token: string; refresh_token: string }>(
      `/auth/callback?code=${encodeURIComponent(code)}`,
    );
    localStorage.setItem(TOKEN_KEY, tokens.access_token);
    setToken(tokens.access_token);
    const result = await apiFetch<Me>("/auth/me", { token: tokens.access_token });
    setMe(result);
    if (result.memberships.length > 0) {
      setCurrentOrgId(result.memberships[0].org_id);
    }
    return result;
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ORG_KEY);
    setToken(null);
    setMe(null);
    setCurrentOrgIdState(null);
  }

  const value = useMemo(
    () => ({ token, me, currentOrgId, isLoading, setCurrentOrgId, login, logout, completeLogin }),
    [token, me, currentOrgId, isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
