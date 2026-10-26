import { apiFetch } from "./client";
import type { RevealedIdentity } from "./types";

/** Ask the server to read the identity hidden in a shared image (PNG or JPEG). */
export function revealIdentity(file: File, signal?: AbortSignal): Promise<RevealedIdentity> {
  const body = new FormData();
  body.append("file", file, file.name);
  return apiFetch<RevealedIdentity>("/stego/reveal", { method: "POST", body, signal });
}
