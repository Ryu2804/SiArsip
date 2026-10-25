"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/patients", label: "Pasien" },
  { href: "/reveal", label: "Ungkap identitas" },
  { href: "/benchmark", label: "Benchmark" },
  { href: "/logs", label: "Log" },
] as const;

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Navigasi utama" className="-mx-1 overflow-x-auto">
      <ul className="flex min-w-max items-center gap-1 px-1">
        {NAV_ITEMS.map(({ href, label }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "inline-flex h-9 items-center rounded-md px-3 text-sm font-medium transition-colors",
                  "focus-visible:ring-ring focus-visible:outline-none focus-visible:ring-2",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
