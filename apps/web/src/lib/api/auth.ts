import { setSession } from "@/lib/auth/token";
import { apiFetch } from "./client";
import type { LoginRequest, LoginResponse, RegisterRequest, User } from "./types";

export async function login(body: LoginRequest): Promise<LoginResponse> {
  const result = await apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body,
    auth: false,
  });
  const { id, name, email } = result;
  setSession(result.jwt_token, JSON.stringify({ id, name, email }));
  return result;
}

export function register(body: RegisterRequest): Promise<User> {
  return apiFetch<User>("/auth/register", {
    method: "POST",
    body,
    auth: false,
  });
}
