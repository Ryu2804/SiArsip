"use client";

import { useMemo, useSyncExternalStore } from "react";

import type { User } from "@/lib/api/types";
import { getToken, getUserRaw, subscribeSession } from "./token";

export type SessionStatus = "loading" | "authenticated" | "unauthenticated";

export type SessionUser = Pick<User, "id" | "name" | "email">;

// `undefined` marks "not read yet": during SSR and hydration the token is
// unknowable, so guards render nothing instead of flashing the wrong screen.
const readToken = (): string | null | undefined => getToken();
const serverToken = (): string | null | undefined => undefined;
const serverUser = (): string | null => null;

export function useSession(): { status: SessionStatus; user: SessionUser | null } {
  const token = useSyncExternalStore(subscribeSession, readToken, serverToken);
  const userRaw = useSyncExternalStore(subscribeSession, getUserRaw, serverUser);

  const user = useMemo<SessionUser | null>(() => {
    if (!userRaw) return null;
    try {
      return JSON.parse(userRaw) as SessionUser;
    } catch {
      return null;
    }
  }, [userRaw]);

  const status: SessionStatus =
    token === undefined ? "loading" : token ? "authenticated" : "unauthenticated";

  return { status, user };
}
