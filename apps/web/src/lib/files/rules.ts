import { ApiError, friendlyMessage } from "@/lib/api/errors";
import type { FileCategory } from "@/lib/api/types";

// Mirrors apps/api: MAX_FILE_BYTES and CATEGORY_RULES in file_service.py. The
// server is authoritative (it checks magic bytes); this only saves a round trip.
export const MAX_FILE_BYTES = 100 * 1024 * 1024;

export interface CategoryInfo {
  value: FileCategory;
  label: string;
  /** Value for <input accept>, a picker hint only. */
  accept: string;
}

export const CATEGORIES: readonly CategoryInfo[] = [
  {
    value: "clinical_image",
    label: "Citra klinis (rontgen, foto luka)",
    accept: ".jpg,.jpeg,.png",
  },
  {
    value: "identity_scan",
    label: "Scan identitas (KTP, BPJS)",
    accept: ".jpg,.jpeg,.png,.pdf",
  },
  {
    value: "office_document",
    label: "Dokumen (persetujuan, rujukan)",
    accept: ".pdf,.docx,.xlsx",
  },
  { value: "video", label: "Video (perawatan luka, USG)", accept: ".mp4" },
];

export function getCategory(value: FileCategory): CategoryInfo {
  return CATEGORIES.find((c) => c.value === value) ?? CATEGORIES[0];
}

const MIME_LABELS: Record<string, string> = {
  "image/jpeg": "JPG",
  "image/png": "PNG",
  "application/pdf": "PDF",
  "video/mp4": "MP4",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "XLSX",
};

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toLocaleString("id-ID", { maximumFractionDigits: 1 })} ${units[unit]}`;
}

/** Client-side pre-check; returns an Indonesian message, or null when fine. */
export function validateFile(file: File): string | null {
  if (file.size === 0) return "File kosong dan tidak dapat diunggah.";
  if (file.size > MAX_FILE_BYTES) {
    return `Ukuran file ${formatBytes(file.size)} melebihi batas ${formatBytes(MAX_FILE_BYTES)}.`;
  }
  return null;
}

/** Specific text for the upload errors the form can act on (413, 415). */
export function describeUploadError(error: unknown, category: FileCategory): string {
  if (error instanceof ApiError) {
    if (error.status === 413) {
      return `Ukuran file melebihi batas ${formatBytes(MAX_FILE_BYTES)}.`;
    }
    if (error.status === 415) {
      const allowed = Array.isArray(error.details.allowed)
        ? (error.details.allowed as string[]).map((m) => MIME_LABELS[m] ?? m)
        : [];
      const where = `kategori “${getCategory(category).label}”`;
      return allowed.length > 0
        ? `Jenis file tidak sesuai untuk ${where}. Jenis yang diizinkan: ${allowed.join(", ")}.`
        : `Jenis file tidak sesuai untuk ${where}.`;
    }
  }
  return friendlyMessage(error);
}
