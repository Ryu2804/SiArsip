import Link from "next/link";

import { AppNav } from "./app-nav";

export function AppHeader() {
  return (
    <header className="bg-background border-b">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
        <Link
          href="/patients"
          className="focus-visible:ring-ring rounded-md text-lg font-semibold tracking-tight focus-visible:outline-none focus-visible:ring-2"
        >
          SiArsip
        </Link>
        <AppNav />
      </div>
    </header>
  );
}
