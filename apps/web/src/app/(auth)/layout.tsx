import { GuestOnly } from "@/components/auth/session-gate";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <GuestOnly>
      <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 px-4 py-12">
        <div className="text-center">
          <p className="text-2xl font-semibold tracking-tight">SiArsip</p>
          <p className="text-muted-foreground mt-1 text-sm">
            Arsip digital terenkripsi untuk dokumentasi pasien
          </p>
        </div>
        <div className="bg-card rounded-xl border p-6">{children}</div>
      </main>
    </GuestOnly>
  );
}
