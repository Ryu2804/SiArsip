import { clearToken, getToken } from "@/lib/auth/token";
import { ApiError } from "./errors";
import type { ApiErrorBody, ApiSuccess } from "./types";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

type JsonBody = Record<string, unknown> | unknown[];

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** Plain objects are sent as JSON; FormData is sent as multipart. */
  body?: JsonBody | FormData;
  query?: Record<string, string | number | boolean | null | undefined>;
  signal?: AbortSignal;
  /**
   * Set false for endpoints that run before sign-in (login, register): no token
   * is attached and a 401 is reported to the caller instead of redirecting.
   */
  auth?: boolean;
}

// The token is already cleared before this runs; navigation needs the Next.js
// router, so <Providers> registers the real handler on mount.
let onUnauthorized = (): void => {};

/** Called after any authenticated request answers 401. */
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

export function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(`${API_URL}${path.startsWith("/") ? path : `/${path}`}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== null && value !== undefined) {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Turn a non-2xx response into an ApiError, whatever shape the body has. */
async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as Partial<ApiErrorBody>;
    if (body.error) {
      return new ApiError(
        response.status,
        body.error.code,
        body.error.message,
        body.error.details,
      );
    }
  } catch {
    // Not JSON (proxy error page, empty body): fall through.
  }
  return new ApiError(
    response.status,
    "http_error",
    response.statusText || `HTTP ${response.status}`,
  );
}

/** Perform a request and return the full `{ data, meta }` envelope. */
export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<ApiSuccess<T>> {
  const { method = "GET", body, query, signal, auth = true } = options;

  const headers: Record<string, string> = {};
  if (auth) Object.assign(headers, authHeaders());

  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body; // the browser sets the multipart boundary itself
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: payload,
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError(0, "network_error", "Network request failed");
  }

  if (!response.ok) {
    const error = await toApiError(response);
    if (response.status === 401 && auth) {
      clearToken();
      onUnauthorized();
    }
    throw error;
  }

  return (await response.json()) as ApiSuccess<T>;
}

/** Perform a request and return just `data`. */
export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const envelope = await apiRequest<T>(path, options);
  return envelope.data as T;
}
