"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useSession } from "@/lib/auth/use-session";

/**
 * Client-side route guard. The token lives in sessionStorage (SIA-39), which
 * server-side middleware cannot read, so protection happens here. The API still
 * enforces authorization on every request; this only decides what to render.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { status } = useSession();

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  if (status !== "authenticated") return null;
  return <>{children}</>;
}

/** Keeps signed-in users away from /login and /register. */
export function GuestOnly({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { status } = useSession();

  useEffect(() => {
    if (status === "authenticated") router.replace("/patients");
  }, [status, router]);

  if (status !== "unauthenticated") return null;
  return <>{children}</>;
}
