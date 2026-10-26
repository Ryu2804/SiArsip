"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FileList } from "@/components/files/file-list";
import { UploadDialog } from "@/components/files/upload-dialog";
import { PatientFormDialog } from "@/components/patients/patient-form-dialog";
import { Button } from "@/components/ui/button";
import { ApiError, friendlyMessage } from "@/lib/api/errors";
import { formatDate, maskNik } from "@/lib/format";
import { useDeletePatient, usePatient } from "@/lib/patients/queries";

export function PatientDetail({ id }: { id: string }) {
  const router = useRouter();
  const { data: patient, error, isPending, refetch } = usePatient(id);
  const remove = useDeletePatient(id);

  const [editing, setEditing] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [showNik, setShowNik] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function confirmDelete() {
    setDeleteError(null);
    try {
      const result = await remove.mutateAsync();
      toast.success(
        result.deleted_files > 0
          ? `Pasien dihapus beserta ${result.deleted_files} file.`
          : "Pasien dihapus.",
      );
      router.replace("/patients");
    } catch (err) {
      setDeleteError(friendlyMessage(err));
    }
  }

  const backLink = (
    <Link
      href="/patients"
      className="text-muted-foreground hover:text-foreground w-fit text-sm underline-offset-4 hover:underline"
    >
      ← Pasien
    </Link>
  );

  if (isPending) {
    return (
      <section className="flex flex-col gap-4">
        {backLink}
        <p role="status" className="text-muted-foreground text-sm">
          Memuat data pasien…
        </p>
      </section>
    );
  }

  if (error || !patient) {
    const notFound = error instanceof ApiError && (error.status === 404 || error.status === 422);
    return (
      <section className="flex flex-col gap-4">
        {backLink}
        <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border p-4">
          <p className="text-destructive text-sm">
            {notFound ? "Pasien tidak ditemukan." : friendlyMessage(error)}
          </p>
          {!notFound && (
            <Button variant="outline" onClick={() => refetch()}>
              Coba lagi
            </Button>
          )}
        </div>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-6">
      {backLink}

      <div className="flex flex-col gap-4 rounded-xl border p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="min-w-0 text-2xl font-semibold tracking-tight break-words">{patient.name}</h1>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setEditing(true)}>
              Ubah
            </Button>
            <Button
              variant="destructive"
              onClick={() => setConfirmingDelete(true)}
              disabled={confirmingDelete}
            >
              Hapus
            </Button>
          </div>
        </div>

        <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
          <Field label="No. RM">
            <span className="font-mono">{patient.mrn}</span>
          </Field>
          <Field label="Tanggal lahir">{formatDate(patient.birth_date)}</Field>
          <Field label="NIK">
            <span className="inline-flex items-center gap-2">
              <span className="font-mono">{showNik ? (patient.nik ?? "-") : maskNik(patient.nik)}</span>
              {patient.nik && (
                <button
                  type="button"
                  onClick={() => setShowNik((v) => !v)}
                  className="text-muted-foreground hover:text-foreground focus-visible:ring-ring rounded text-xs underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2"
                >
                  {showNik ? "Sembunyikan" : "Tampilkan"}
                </button>
              )}
            </span>
          </Field>
          <Field label="Diagnosis">{patient.diagnosis ?? "-"}</Field>
        </dl>
      </div>

      {confirmingDelete && (
        <div
          role="alertdialog"
          aria-labelledby="hapus-judul"
          aria-describedby="hapus-isi"
          className="border-destructive/40 bg-destructive/5 flex flex-col gap-3 rounded-xl border p-5"
        >
          <h2 id="hapus-judul" className="font-semibold">
            Hapus pasien ini?
          </h2>
          <p id="hapus-isi" className="text-sm">
            Semua file milik pasien juga akan terhapus dan tidak dapat dikembalikan.
          </p>
          {deleteError && (
            <p role="alert" className="text-destructive text-sm">
              {deleteError}
            </p>
          )}
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setConfirmingDelete(false);
                setDeleteError(null);
              }}
              disabled={remove.isPending}
            >
              Batal
            </Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={remove.isPending}>
              {remove.isPending ? "Menghapus…" : "Ya, hapus"}
            </Button>
          </div>
        </div>
      )}

      <FileList patientId={id} onUpload={() => setUploadOpen(true)} />

      <UploadDialog patientId={id} open={uploadOpen} onOpenChange={setUploadOpen} />

      <PatientFormDialog open={editing} onOpenChange={setEditing} patient={patient} onSaved={() => toast.success("Data pasien diperbarui.")} />
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="break-words">{children}</dd>
    </div>
  );
}
