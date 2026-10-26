import Link from "next/link";

import { AppNav } from "./app-nav";
import { UserMenu } from "./user-menu";

export function AppHeader() {
  return (
    <header className="bg-background border-b">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3">
        <Link
          href="/patients"
          className="focus-visible:ring-ring rounded-md text-lg font-semibold tracking-tight focus-visible:outline-none focus-visible:ring-2"
        >
          SiArsip
        </Link>
        <div className="order-3 w-full sm:order-2 sm:w-auto sm:flex-1">
          <AppNav />
        </div>
        <div className="order-2 sm:order-3">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
