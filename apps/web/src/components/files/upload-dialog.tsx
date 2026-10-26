"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";
import { toast } from "sonner";

import { CipherBadge } from "@/components/cipher-badge";
import { Dropzone } from "@/components/files/dropzone";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { uploadFile } from "@/lib/api/files";
import type { CipherChoice, FileCategory, FileRecord } from "@/lib/api/types";
import { CIPHERS, getCipherInfo } from "@/lib/ciphers";
import { fileKeys } from "@/lib/files/queries";
import {
  CATEGORIES,
  describeUploadError,
  formatBytes,
  getCategory,
  validateFile,
} from "@/lib/files/rules";

interface UploadDialogProps {
  patientId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUploaded?: (file: FileRecord) => void;
}

export function UploadDialog({ patientId, open, onOpenChange, onUploaded }: UploadDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Unggah file</DialogTitle>
          <DialogDescription>
            File dienkripsi di server sebelum disimpan. Pilih cipher dengan hati-hati.
          </DialogDescription>
        </DialogHeader>
        {/* Mounted only while open: closing resets the form and cancels any upload. */}
        <UploadForm
          patientId={patientId}
          onClose={() => onOpenChange(false)}
          onUploaded={onUploaded}
        />
      </DialogContent>
    </Dialog>
  );
}

type Phase = "idle" | "uploading";

const categoryItems = CATEGORIES.map((c) => ({ value: c.value, label: c.label }));
const cipherItems = CIPHERS.map((c) => ({
  value: c.choice,
  label: `${c.label} · ${c.recommended ? "Direkomendasikan" : "Tidak disarankan"}`,
}));

function UploadForm({
  patientId,
  onClose,
  onUploaded,
}: {
  patientId: string;
  onClose: () => void;
  onUploaded?: (file: FileRecord) => void;
}) {
  const queryClient = useQueryClient();
  const ids = useId();
  const abortRef = useRef<AbortController | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [category, setCategory] = useState<FileCategory | null>(null);
  const [categoryError, setCategoryError] = useState<string | null>(null);
  const [cipher, setCipher] = useState<CipherChoice>("aes");
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);
  const [formError, setFormError] = useState<string | null>(null);

  // Closing the dialog unmounts this form; stop any request still in flight.
  useEffect(() => () => abortRef.current?.abort(), []);

  const uploading = phase === "uploading";
  const cipherInfo = getCipherInfo(cipher);

  function pickFile(next: File) {
    const problem = validateFile(next);
    setFormError(null);
    setFileError(problem);
    setFile(problem ? null : next);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);

    if (!file) setFileError("Pilih file yang akan diunggah.");
    if (!category) setCategoryError("Pilih kategori file.");
    if (!file || !category) return;

    const controller = new AbortController();
    abortRef.current = controller;
    setPhase("uploading");
    setProgress(0);

    try {
      const record = await uploadFile(
        patientId,
        { file, category, cipher },
        { onProgress: setProgress, signal: controller.signal },
      );
      await queryClient.invalidateQueries({ queryKey: fileKeys.byPatient(patientId) });
      toast.success(`“${record.original_name}” diunggah dan dienkripsi (${cipherInfo.label}).`);
      onUploaded?.(record);
      onClose();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setFormError(describeUploadError(error, category));
      setPhase("idle");
    }
  }

  const serverWorking = uploading && progress >= 1;
  const fileErrorId = `${ids}-file-error`;

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      {formError && (
        <p role="alert" className="bg-destructive/10 text-destructive rounded-lg px-3 py-2 text-sm">
          {formError}
        </p>
      )}

      <div className="flex flex-col gap-2">
        <Dropzone
          onFile={pickFile}
          accept={category ? getCategory(category).accept : undefined}
          disabled={uploading}
          invalid={Boolean(fileError)}
          describedBy={fileError ? fileErrorId : undefined}
        />
        {fileError && (
          <p id={fileErrorId} className="text-destructive text-sm">
            {fileError}
          </p>
        )}
        {file && (
          <div className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm">
            <span className="min-w-0 truncate" title={file.name}>
              {file.name}
            </span>
            <span className="text-muted-foreground shrink-0">{formatBytes(file.size)}</span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={uploading}
              onClick={() => setFile(null)}
              aria-label={`Hapus ${file.name} dari unggahan`}
            >
              Hapus
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`${ids}-category`}>Kategori *</Label>
        <Select
          items={categoryItems}
          value={category}
          disabled={uploading}
          onValueChange={(value) => {
            setCategory(value as FileCategory | null);
            setCategoryError(null);
          }}
        >
          <SelectTrigger
            id={`${ids}-category`}
            className="w-full"
            aria-invalid={categoryError ? true : undefined}
          >
            <SelectValue placeholder="Pilih kategori" />
          </SelectTrigger>
          <SelectContent>
            {CATEGORIES.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {categoryError && <p className="text-destructive text-sm">{categoryError}</p>}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`${ids}-cipher`}>Cipher</Label>
        <Select
          items={cipherItems}
          value={cipher}
          disabled={uploading}
          onValueChange={(value) => value && setCipher(value as CipherChoice)}
        >
          <SelectTrigger id={`${ids}-cipher`} className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CIPHERS.map((c) => (
              <SelectItem key={c.choice} value={c.choice}>
                <CipherBadge algorithm={c.choice} showAdvice />
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p
          className={
            cipherInfo.recommended ? "text-muted-foreground text-xs" : "text-destructive text-xs"
          }
        >
          {cipherInfo.recommended ? "" : "Peringatan: "}
          {cipherInfo.note}
        </p>
      </div>

      {uploading && (
        <div className="flex flex-col gap-1.5" role="status">
          <Progress
            label="Kemajuan unggahan"
            value={serverWorking ? undefined : progress * 100}
          />
          <p className="text-muted-foreground text-xs">
            {serverWorking
              ? "Memproses dan mengenkripsi di server…"
              : `Mengunggah… ${Math.round(progress * 100)}%`}
          </p>
        </div>
      )}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          {uploading ? "Batalkan unggahan" : "Batal"}
        </Button>
        <Button type="submit" disabled={uploading}>
          {uploading ? "Mengunggah…" : "Unggah"}
        </Button>
      </DialogFooter>
    </form>
  );
}
