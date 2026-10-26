"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { Dropzone } from "@/components/files/dropzone";
import { Button, buttonVariants } from "@/components/ui/button";
import { revealIdentity } from "@/lib/api/stego";
import { formatDate } from "@/lib/format";
import { formatBytes } from "@/lib/files/rules";
import {
  REVEAL_ACCEPT,
  describeRevealError,
  validateRevealFile,
} from "@/lib/stego/reveal";

export function RevealView() {
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  // gcTime 0: the identity lives only in this component, not in the query cache.
  const reveal = useMutation({
    mutationFn: (image: File) => revealIdentity(image),
    gcTime: 0,
  });

  function pick(next: File) {
    const problem = validateRevealFile(next);
    setFileError(problem);
    reveal.reset();
    if (problem) {
      setFile(null);
      return;
    }
    setFile(next);
    reveal.mutate(next);
  }

  function clear() {
    setFile(null);
    setFileError(null);
    reveal.reset();
  }

  const identity = reveal.data;

  return (
    <section className="flex max-w-2xl flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Ungkap identitas</h1>
        <p className="text-muted-foreground text-sm">
          Unggah gambar konsultasi yang Anda unduh dari daftar file untuk membaca identitas
          pasien yang tersembunyi di dalamnya. Hanya akun yang membuat gambar itu yang bisa
          membacanya.
        </p>
      </div>

      <p role="note" className="bg-muted rounded-lg border px-3 py-2 text-sm">
        <strong>Perhatian:</strong> identitas hilang jika gambar dikirim ulang sebagai foto
        (misalnya lewat WhatsApp), karena gambar dikompres ulang menjadi JPEG. Kirim sebagai
        file atau dokumen agar tetap bisa dibaca.
      </p>

      <Dropzone
        onFile={pick}
        accept={REVEAL_ACCEPT}
        disabled={reveal.isPending}
        invalid={Boolean(fileError)}
        describedBy={fileError ? "reveal-file-error" : undefined}
        hint="PNG atau JPEG, maksimal 100 MB"
      />
      {fileError && (
        <p id="reveal-file-error" role="alert" className="text-destructive text-sm">
          {fileError}
        </p>
      )}

      {file && (
        <div className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm">
          <span className="min-w-0 truncate" title={file.name}>
            {file.name}
          </span>
          <span className="text-muted-foreground shrink-0">{formatBytes(file.size)}</span>
        </div>
      )}

      {reveal.isPending && (
        <p role="status" className="text-muted-foreground text-sm">
          Membaca dan mendekripsi identitas…
        </p>
      )}

      {reveal.error && (
        <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border p-4">
          <p className="text-sm font-medium">{describeRevealError(reveal.error)}</p>
          <Button variant="outline" onClick={clear}>
            Coba gambar lain
          </Button>
        </div>
      )}

      {identity && (
        <div className="flex flex-col gap-4 rounded-xl border p-5" role="status">
          <h2 className="font-semibold">Identitas pasien</h2>
          <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
            <Field label="Nama">{identity.name}</Field>
            <Field label="No. RM">
              <span className="font-mono">{identity.mrn}</span>
            </Field>
            <Field label="Tanggal lahir">{formatDate(identity.birth_date)}</Field>
            <Field label="Diagnosis">{identity.diagnosis ?? "-"}</Field>
          </dl>
          <div className="flex flex-wrap gap-2">
            <Link
              href={`/patients/${identity.patient_id}`}
              className={buttonVariants({ variant: "default" })}
            >
              Buka data pasien
            </Link>
            <Button variant="outline" onClick={clear}>
              Bersihkan hasil
            </Button>
          </div>
        </div>
      )}
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
