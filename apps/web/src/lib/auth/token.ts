// MVP decision (SIA-39): the JWT lives in sessionStorage and is dropped on logout.
// Every access is wrapped because storage can be blocked or unavailable (SSR,
// private windows), and the app must still render without it.
//
// The signed-in user's display info is stored beside the token and cleared with
// it, so "the session" is always both keys or neither.

const TOKEN_KEY = "siarsip.token";
const USER_KEY = "siarsip.user";

const listeners = new Set<() => void>();

function notify(): void {
  listeners.forEach((listener) => listener());
}

/** For useSyncExternalStore: fires on sign-in, sign-out, and 401 clean-up. */
export function subscribeSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function read(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return read(TOKEN_KEY);
}

/** Raw JSON string, so the value stays referentially stable between reads. */
export function getUserRaw(): string | null {
  return read(USER_KEY);
}

/** Store the user first, then the token: subscribers fire on the token write. */
export function setSession(token: string, userJson: string): void {
  try {
    window.sessionStorage.setItem(USER_KEY, userJson);
    window.sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Storage unavailable: the user will simply be asked to sign in again.
  }
  notify();
}

export function clearToken(): void {
  try {
    window.sessionStorage.removeItem(TOKEN_KEY);
    window.sessionStorage.removeItem(USER_KEY);
  } catch {
    // Nothing to clear.
  }
  notify();
}
