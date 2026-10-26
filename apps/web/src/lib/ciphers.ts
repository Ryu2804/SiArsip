import type { CipherAlgorithm, CipherChoice } from "@/lib/api/types";

export interface CipherInfo {
  /** Short name the upload form sends as `cipher`. */
  choice: CipherChoice;
  /** Name stored on the file record. */
  algorithm: CipherAlgorithm;
  label: string;
  recommended: boolean;
  /** One-line security note, reused by the upload form and the benchmark page. */
  note: string;
}

export const CIPHERS: readonly CipherInfo[] = [
  {
    choice: "aes",
    algorithm: "aes-gcm",
    label: "AES-GCM",
    recommended: true,
    note: "Standar modern dengan autentikasi bawaan. Direkomendasikan untuk semua data.",
  },
  {
    choice: "des",
    algorithm: "des-cbc",
    label: "DES-CBC",
    recommended: false,
    note: "Kunci 56-bit sudah usang dan dapat dipecahkan. Hanya untuk perbandingan.",
  },
  {
    choice: "rc4",
    algorithm: "rc4",
    label: "RC4",
    recommended: false,
    note: "Stream cipher usang dengan kelemahan bias keystream. Hanya untuk perbandingan.",
  },
];

/** Look up by either the form value ("aes") or the stored value ("aes-gcm"). */
export function getCipherInfo(value: CipherAlgorithm | CipherChoice): CipherInfo {
  const found = CIPHERS.find((c) => c.choice === value || c.algorithm === value);
  if (!found) throw new Error(`Unknown cipher: ${value}`);
  return found;
}
