// Mirrors apps/api/app/schemas. Hand-written for now; replace with types
// generated from the FastAPI OpenAPI schema once the contract settles.

export interface Meta {
  page: number;
  size: number;
  total: number;
}

export interface ApiSuccess<T> {
  success: true;
  message: string;
  data: T | null;
  meta: Meta | null;
}

export interface ApiErrorBody {
  success: false;
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}

// ---------- Auth ----------

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface LoginResponse extends User {
  jwt_token: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest extends LoginRequest {
  name: string;
}

// ---------- Patients ----------

export interface Patient {
  id: string;
  name: string;
  mrn: string;
  nik: string | null;
  birth_date: string | null;
  diagnosis: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientListItem {
  id: string;
  name: string;
  mrn: string;
  nik_masked: string | null;
  birth_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientInput {
  name: string;
  mrn: string;
  nik?: string | null;
  birth_date?: string | null;
  diagnosis?: string | null;
}

export interface PatientDeleteResponse {
  id: string;
  deleted_files: number;
}

// ---------- Files ----------

export type FileCategory =
  | "identity_scan"
  | "office_document"
  | "video"
  | "clinical_image";

export type PdpClass = "specific" | "general";

export type CipherAlgorithm = "aes-gcm" | "des-cbc" | "rc4";

/** Short names accepted by the upload form (`cipher` field). */
export type CipherChoice = "aes" | "des" | "rc4";

export interface FileRecord {
  id: string;
  patient_id: string;
  original_name: string;
  category: FileCategory;
  pdp_class: PdpClass;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  algorithm: CipherAlgorithm;
  shareable: boolean;
  created_at: string;
}

// ---------- Activity log ----------

export type ActivityAction =
  | "upload"
  | "download"
  | "view"
  | "update"
  | "delete"
  | "login"
  | "logout"
  | "share_image";

export interface ActivityLog {
  id: number;
  action: ActivityAction;
  file_id: string | null;
  created_at: string;
}

// ---------- Stego reveal ----------

export interface RevealedIdentity {
  patient_id: string;
  name: string;
  mrn: string;
  birth_date: string | null;
  diagnosis: string | null;
}

// ---------- Benchmark ----------

export interface BenchmarkRequest {
  size_bytes: number;
  iterations: number;
}

export interface CipherBenchmark {
  algorithm: CipherAlgorithm;
  size_bytes: number;
  iterations: number;
  /** Average per single operation. */
  encrypt_ms: number;
  decrypt_ms: number;
  encrypt_total_ms: number;
  decrypt_total_ms: number;
  total_ms: number;
  encrypt_mb_s: number;
  decrypt_mb_s: number;
  overhead_bytes: number;
  overhead_percent: number;
  verified: boolean;
  tamper_detected: boolean;
}

export interface BenchmarkResult {
  size_bytes: number;
  iterations: number;
  results: CipherBenchmark[];
}
