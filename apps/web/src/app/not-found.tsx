import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center gap-4 px-4 py-24 text-center">
      <p className="text-muted-foreground text-sm font-medium">404</p>
      <h1 className="text-2xl font-semibold tracking-tight">
        Halaman tidak ditemukan
      </h1>
      <p className="text-muted-foreground text-sm">
        Alamat yang Anda buka tidak ada atau sudah dipindahkan.
      </p>
      <Link
        href="/patients"
        className="bg-primary text-primary-foreground focus-visible:ring-ring inline-flex h-9 items-center rounded-md px-4 text-sm font-medium focus-visible:outline-none focus-visible:ring-2"
      >
        Kembali ke daftar pasien
      </Link>
    </main>
  );
}
