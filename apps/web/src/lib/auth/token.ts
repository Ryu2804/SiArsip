// MVP decision (SIA-39): the JWT lives in sessionStorage and is dropped on logout.
// Every access is wrapped because storage can be blocked or unavailable (SSR,
// private windows), and the app must still render without it.

const TOKEN_KEY = "siarsip.token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    window.sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Storage unavailable: the user will simply be asked to sign in again.
  }
}

export function clearToken(): void {
  try {
    window.sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Nothing to clear.
  }
}
