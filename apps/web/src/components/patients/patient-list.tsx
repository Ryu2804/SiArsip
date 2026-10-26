"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { PatientFormDialog } from "@/components/patients/patient-form-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { friendlyMessage } from "@/lib/api/errors";
import { formatDate } from "@/lib/format";
import { usePatients } from "@/lib/patients/queries";

const PAGE_SIZE = 20;

export function PatientList() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);

  const { data, error, isPending, isFetching, refetch } = usePatients(page, PAGE_SIZE);

  const query = search.trim().toLowerCase();
  const rows = (data?.items ?? []).filter(
    (p) => !query || p.name.toLowerCase().includes(query) || p.mrn.toLowerCase().includes(query),
  );
  const total = data?.meta.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Pasien</h1>
        <Button size="lg" onClick={() => setCreating(true)}>
          + Tambah pasien
        </Button>
      </div>

      <div className="max-w-sm">
        <label htmlFor="cari-pasien" className="sr-only">
          Cari nama atau No. RM
        </label>
        <Input
          id="cari-pasien"
          type="search"
          placeholder="Cari nama atau No. RM"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {isPending ? (
        <p role="status" className="text-muted-foreground text-sm">
          Memuat daftar pasien…
        </p>
      ) : error ? (
        <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border p-4">
          <p className="text-destructive text-sm">{friendlyMessage(error)}</p>
          <Button variant="outline" onClick={() => refetch()}>
            Coba lagi
          </Button>
        </div>
      ) : total === 0 ? (
        <div className="flex flex-col items-start gap-3 rounded-lg border border-dashed p-6">
          <p className="text-muted-foreground text-sm">
            Belum ada pasien. Tambahkan pasien pertama.
          </p>
          <Button onClick={() => setCreating(true)}>+ Tambah pasien</Button>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>No. RM</TableHead>
                  <TableHead>Nama</TableHead>
                  <TableHead>NIK</TableHead>
                  <TableHead>Tanggal lahir</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-muted-foreground py-6 text-center">
                      Tidak ada pasien yang cocok di halaman ini.
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((patient) => (
                    <TableRow key={patient.id}>
                      <TableCell className="font-mono text-sm">{patient.mrn}</TableCell>
                      <TableCell>
                        <Link
                          href={`/patients/${patient.id}`}
                          className="focus-visible:ring-ring -m-1 rounded p-1 font-medium underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2"
                        >
                          {patient.name}
                        </Link>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {patient.nik_masked ?? "-"}
                      </TableCell>
                      <TableCell>{formatDate(patient.birth_date)}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="text-muted-foreground" aria-live="polite">
              Halaman {page} dari {totalPages} · {total} pasien
              {totalPages > 1 && " · pencarian hanya menyaring halaman ini"}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                disabled={page <= 1 || isFetching}
                onClick={() => setPage((p) => p - 1)}
              >
                Sebelumnya
              </Button>
              <Button
                variant="outline"
                disabled={page >= totalPages || isFetching}
                onClick={() => setPage((p) => p + 1)}
              >
                Berikutnya
              </Button>
            </div>
          </div>
        </>
      )}

      <PatientFormDialog
        open={creating}
        onOpenChange={setCreating}
        onSaved={(patient) => {
          toast.success("Pasien berhasil ditambahkan.");
          router.push(`/patients/${patient.id}`);
        }}
      />
    </section>
  );
}
