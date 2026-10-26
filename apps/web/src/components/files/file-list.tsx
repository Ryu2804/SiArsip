"use client";

import { useState } from "react";
import { toast } from "sonner";

import { CipherBadge } from "@/components/cipher-badge";
import { FilePreviewDialog } from "@/components/files/file-preview-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { friendlyMessage } from "@/lib/api/errors";
import { downloadFileBlob, shareImageBlob } from "@/lib/api/files";
import type { FileCategory, FileRecord } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { usePatientFiles } from "@/lib/files/queries";
import { CATEGORIES, formatBytes, getCategory } from "@/lib/files/rules";
import { previewKind, saveBlob } from "@/lib/files/save";

const PAGE_SIZE = 20;
const ALL = "all";

const categoryItems = [
  { value: ALL, label: "Semua kategori" },
  ...CATEGORIES.map((c) => ({ value: c.value, label: c.label })),
];

export function FileList({ patientId, onUpload }: { patientId: string; onUpload: () => void }) {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState<FileCategory | typeof ALL>(ALL);
  const [previewing, setPreviewing] = useState<FileRecord | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const { data, error, isPending, isFetching, refetch } = usePatientFiles(
    patientId,
    page,
    PAGE_SIZE,
    category === ALL ? undefined : category,
  );

  const total = data?.meta.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  async function run(file: FileRecord, task: () => Promise<void>) {
    setBusyId(file.id);
    try {
      await task();
    } catch (err) {
      toast.error(friendlyMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  const download = (file: FileRecord) =>
    run(file, async () => saveBlob(await downloadFileBlob(file.id), file.original_name));

  const downloadShared = (file: FileRecord) =>
    run(file, async () => {
      const blob = await shareImageBlob(file.id);
      // Named by file id: the original name can carry patient identity.
      saveBlob(blob, `konsultasi-${file.id}.${blob.type === "image/png" ? "png" : "jpg"}`);
      toast.success("Gambar konsultasi diunduh. Identitas pasien tidak disertakan.");
    });

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">File</h2>
        <div className="flex flex-wrap items-center gap-2">
          <Select
            items={categoryItems}
            value={category}
            onValueChange={(value) => {
              setCategory((value as FileCategory | typeof ALL | null) ?? ALL);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-56" aria-label="Filter kategori">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {categoryItems.map((c) => (
                <SelectItem key={c.value} value={c.value}>
                  {c.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={onUpload}>+ Unggah file</Button>
        </div>
      </div>

      {isPending ? (
        <p role="status" className="text-muted-foreground text-sm">
          Memuat daftar file…
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
            {category === ALL
              ? "Belum ada file untuk pasien ini."
              : "Tidak ada file di kategori ini."}
          </p>
          {category === ALL && <Button onClick={onUpload}>+ Unggah file pertama</Button>}
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nama file</TableHead>
                  <TableHead>Kategori</TableHead>
                  <TableHead>Cipher</TableHead>
                  <TableHead>Ukuran</TableHead>
                  <TableHead>Diunggah</TableHead>
                  <TableHead>
                    <span className="sr-only">Aksi</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((file) => {
                  const busy = busyId === file.id;
                  return (
                    <TableRow key={file.id}>
                      <TableCell className="max-w-64 truncate font-medium" title={file.original_name}>
                        {file.original_name}
                      </TableCell>
                      <TableCell>
                        <span className="flex flex-col items-start gap-1">
                          <span className="text-sm">{getCategory(file.category).label}</span>
                          {file.pdp_class === "specific" && (
                            <Badge variant="outline">Data spesifik</Badge>
                          )}
                        </span>
                      </TableCell>
                      <TableCell>
                        <CipherBadge algorithm={file.algorithm} />
                      </TableCell>
                      <TableCell>{formatBytes(file.size_bytes)}</TableCell>
                      <TableCell>{formatDateTime(file.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap justify-end gap-2">
                          {previewKind(file.mime_type) && (
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={busy}
                              onClick={() => setPreviewing(file)}
                              aria-label={`Pratinjau ${file.original_name}`}
                            >
                              Pratinjau
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={busy}
                            onClick={() => download(file)}
                            aria-label={`Unduh ${file.original_name}`}
                          >
                            {busy ? "Memproses…" : "Unduh"}
                          </Button>
                          {file.shareable && (
                            <Button
                              variant="secondary"
                              size="sm"
                              disabled={busy}
                              onClick={() => downloadShared(file)}
                              aria-label={`Unduh untuk konsultasi: ${file.original_name}`}
                            >
                              Unduh untuk konsultasi
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="text-muted-foreground" aria-live="polite">
              Halaman {page} dari {totalPages} · {total} file
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

      <FilePreviewDialog
        file={previewing}
        onOpenChange={(open) => {
          if (!open) setPreviewing(null);
        }}
      />
    </div>
  );
}
