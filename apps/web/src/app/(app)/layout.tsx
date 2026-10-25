import { AppHeader } from "@/components/layout/app-header";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <a
        href="#konten"
        className="bg-background sr-only rounded-md px-3 py-2 text-sm focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50"
      >
        Lewati ke konten
      </a>
      <AppHeader />
      <main id="konten" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        {children}
      </main>
    </>
  );
}
