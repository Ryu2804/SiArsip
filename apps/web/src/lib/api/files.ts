import {
  authHeaders,
  buildUrl,
  parseApiError,
  reportUnauthorized,
} from "./client";
import { ApiError } from "./errors";
import type { ApiSuccess, CipherChoice, FileCategory, FileRecord } from "./types";

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
