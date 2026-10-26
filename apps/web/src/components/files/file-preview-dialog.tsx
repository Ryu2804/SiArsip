"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { downloadFileBlob } from "@/lib/api/files";
import { friendlyMessage } from "@/lib/api/errors";
import type { FileRecord } from "@/lib/api/types";
import { fileKeys } from "@/lib/files/queries";
import { previewKind, saveBlob, type PreviewKind } from "@/lib/files/save";

interface FilePreviewDialogProps {
  file: FileRecord | null;
  onOpenChange: (open: boolean) => void;
}

export function FilePreviewDialog({ file, onOpenChange }: FilePreviewDialogProps) {
  return (
    <Dialog open={file !== null} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Pratinjau file</DialogTitle>
          <DialogDescription>
            File didekripsi oleh server hanya untuk ditampilkan di sini dan tidak disimpan di
            peramban.
          </DialogDescription>
        </DialogHeader>
        {/* Mounted only while open, so closing frees the decrypted blob. */}
        {file && <PreviewBody file={file} onClose={() => onOpenChange(false)} />}
      </DialogContent>
    </Dialog>
  );
}

function PreviewBody({ file, onClose }: { file: FileRecord; onClose: () => void }) {
  const kind = previewKind(file.mime_type);
  const {
    data: blob,
    error,
    isPending,
    refetch,
  } = useQuery({
    queryKey: fileKeys.preview(file.id),
    queryFn: ({ signal }) => downloadFileBlob(file.id, signal),
    enabled: kind !== null,
    gcTime: 0, // never keep decrypted content in the query cache
    staleTime: 0,
    retry: false,
  });

  // An object URL is a resource outside React: create it with the blob, revoke it
  // when the blob goes away. (Creating it during render would leak on re-render.)
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!blob) return;
    const objectUrl = URL.createObjectURL(blob);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- mirrors an external resource
    setUrl(objectUrl);
    return () => {
      URL.revokeObjectURL(objectUrl);
      setUrl(null);
    };
  }, [blob]);

  return (
    <div className="flex flex-col gap-4">
      <p className="truncate text-sm font-medium" title={file.original_name}>
        {file.original_name}
      </p>

      <div className="bg-muted/40 flex min-h-48 items-center justify-center overflow-hidden rounded-lg border">
        {kind === null ? (
          <p className="text-muted-foreground p-6 text-center text-sm">
            Jenis file ini tidak bisa dipratinjau. Gunakan tombol Unduh.
          </p>
        ) : error ? (
          <div role="alert" className="flex flex-col items-center gap-3 p-6">
            <p className="text-destructive text-sm">{friendlyMessage(error)}</p>
            <Button variant="outline" onClick={() => refetch()}>
              Coba lagi
            </Button>
          </div>
        ) : isPending || !url ? (
          <p role="status" className="text-muted-foreground p-6 text-sm">
            Mendekripsi dan memuat file…
          </p>
        ) : (
          <PreviewMedia kind={kind} url={url} name={file.original_name} />
        )}
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Tutup
        </Button>
        {blob && (
          <Button onClick={() => saveBlob(blob, file.original_name)}>Unduh</Button>
        )}
      </DialogFooter>
    </div>
  );
}

function PreviewMedia({ kind, url, name }: { kind: PreviewKind; url: string; name: string }) {
  if (kind === "image") {
    // eslint-disable-next-line @next/next/no-img-element -- blob: URL, next/image cannot optimise it
    return <img src={url} alt={`Pratinjau ${name}`} className="max-h-[70vh] w-auto object-contain" />;
  }
  if (kind === "video") {
    return <video src={url} controls className="max-h-[70vh] w-full" aria-label={`Video ${name}`} />;
  }
  return <iframe src={url} title={`Dokumen ${name}`} className="h-[70vh] w-full" />;
}
