import { useAuth } from "./auth";
import { apiFetch } from "./api";

/** Returns a fetch function pre-bound to the current session's token + org,
 * for use as a react-query queryFn. */
export function useOrgFetch() {
  const { token, currentOrgId } = useAuth();

  return function orgFetch<T>(path: string): Promise<T> {
    if (!token || !currentOrgId) {
      return Promise.reject(new Error("Not authenticated"));
    }
    return apiFetch<T>(path, { token, orgId: currentOrgId });
  };
}
