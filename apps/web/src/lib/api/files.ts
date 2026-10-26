import {
  apiRequest,
  authHeaders,
  buildUrl,
  parseApiError,
  reportUnauthorized,
} from "./client";
import { ApiError } from "./errors";
import type {
  ApiSuccess,
  CipherChoice,
  FileCategory,
  FileRecord,
  Meta,
} from "./types";

export interface UploadInput {
  file: File;
  category: FileCategory;
  cipher: CipherChoice;
}

export interface UploadOptions {
  /** Fraction (0..1) of the request body sent so far. */
  onProgress?: (fraction: number) => void;
  signal?: AbortSignal;
}

/**
 * Upload with progress. fetch() cannot report upload progress, so this uses
 * XMLHttpRequest while keeping the same auth, 401 and error behaviour as apiFetch.
 */
export function uploadFile(
  patientId: string,
  { file, category, cipher }: UploadInput,
  { onProgress, signal }: UploadOptions = {},
): Promise<FileRecord> {
  return new Promise<FileRecord>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Upload dibatalkan", "AbortError"));
      return;
    }

    const xhr = new XMLHttpRequest();
    xhr.open("POST", buildUrl(`/patients/${patientId}/files`));
    for (const [name, value] of Object.entries(authHeaders())) {
      xhr.setRequestHeader(name, value);
    }

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(event.loaded / event.total);
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const envelope = JSON.parse(xhr.responseText) as ApiSuccess<FileRecord>;
          resolve(envelope.data as FileRecord);
        } catch {
          reject(new ApiError(xhr.status, "invalid_response", "Respons server tidak valid"));
        }
        return;
      }
      if (xhr.status === 401) reportUnauthorized();
      reject(parseApiError(xhr.status, xhr.statusText, xhr.responseText));
    };

    xhr.onerror = () => reject(new ApiError(0, "network_error", "Network request failed"));
    xhr.onabort = () => reject(new DOMException("Upload dibatalkan", "AbortError"));
    signal?.addEventListener("abort", () => xhr.abort(), { once: true });

    const body = new FormData();
    body.append("category", category);
    body.append("cipher", cipher);
    body.append("file", file, file.name);
    xhr.send(body);
  });
}

export interface PatientFilePage {
  items: FileRecord[];
  meta: Meta;
}

/** Files of one patient, newest first. Metadata only, no content. */
export async function listPatientFiles(
  patientId: string,
  page: number,
  size: number,
  category?: FileCategory,
  signal?: AbortSignal,
): Promise<PatientFilePage> {
  const envelope = await apiRequest<FileRecord[]>(
    `/patients/${patientId}/files`,
    { query: { page, size, category }, signal },
  );
  const items = envelope.data ?? [];
  return { items, meta: envelope.meta ?? { page, size, total: items.length } };
}

async function fetchBlob(
  path: string,
  method: "GET" | "POST",
  signal?: AbortSignal,
): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path), { method, headers: authHeaders(), signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "Network request failed");
  }
  if (!response.ok) {
    const error = parseApiError(response.status, response.statusText, await response.text());
    if (response.status === 401) reportUnauthorized();
    throw error;
  }
  return response.blob();
}

/** Decrypted file content. The Authorization header rules out a plain <a href>. */
export function downloadFileBlob(fileId: string, signal?: AbortSignal): Promise<Blob> {
  return fetchBlob(`/files/${fileId}/download`, "GET", signal);
}

/** Image prepared for sharing (clinical images only): no patient identity inside. */
export function shareImageBlob(fileId: string, signal?: AbortSignal): Promise<Blob> {
  return fetchBlob(`/files/${fileId}/share-image`, "POST", signal);
}
