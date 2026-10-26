"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { clearToken } from "@/lib/auth/token";
import { useSession } from "@/lib/auth/use-session";

export function UserMenu() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useSession();

  function logout() {
    clearToken();
    queryClient.clear(); // never leave the previous user's patient data cached
    router.replace("/login");
  }

  return (
    <div className="flex items-center gap-3">
      {user && (
        <span className="text-muted-foreground max-w-40 truncate text-sm" title={user.email}>
          {user.name}
        </span>
      )}
      <Button variant="outline" onClick={logout}>
        Keluar
      </Button>
    </div>
  );
}
