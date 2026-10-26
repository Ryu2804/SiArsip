import { ApiError, friendlyMessage } from "@/lib/api/errors";
import { MAX_FILE_BYTES, formatBytes } from "@/lib/files/rules";

export const REVEAL_ACCEPT = ".png,.jpg,.jpeg";

/** Shown for every "could not read it" outcome, so a failure never says why. */
export const NO_IDENTITY_MESSAGE = "Tidak ada identitas yang bisa dibaca dari gambar ini.";

/** Client-side pre-check; returns an Indonesian message, or null when fine. */
export function validateRevealFile(file: File): string | null {
  if (!/\.(png|jpe?g)$/i.test(file.name)) return "Hanya gambar PNG atau JPEG yang bisa dibaca.";
  if (file.size === 0) return "File kosong.";
  if (file.size > MAX_FILE_BYTES) {
    return `Ukuran file maksimal ${formatBytes(MAX_FILE_BYTES)}.`;
  }
  return null;
}

/**
 * The server reports wrong owner, no payload and a damaged payload as the same
 * `reveal_failed`; the reason in `details` is deliberately not surfaced.
 */
export function describeRevealError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "reveal_failed") return NO_IDENTITY_MESSAGE;
    if (error.status === 415) return "Hanya gambar PNG atau JPEG yang bisa dibaca.";
  }
  return friendlyMessage(error);
}
