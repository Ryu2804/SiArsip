/** Hand a blob to the browser as a download, then release the object URL. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // The click only queues the download; revoke after it has started.
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export type PreviewKind = "image" | "pdf" | "video";

/** What the preview dialog can render inline; Office files have no preview. */
export function previewKind(mimeType: string): PreviewKind | null {
  if (mimeType === "image/jpeg" || mimeType === "image/png") return "image";
  if (mimeType === "application/pdf") return "pdf";
  if (mimeType === "video/mp4") return "video";
  return null;
}
