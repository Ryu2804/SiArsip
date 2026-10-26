import { apiFetch, apiRequest } from "./client";
import type {
  Meta,
  Patient,
  PatientDeleteResponse,
  PatientInput,
  PatientListItem,
} from "./types";

export interface PatientPage {
  items: PatientListItem[];
  meta: Meta;
}

export async function listPatients(
  page: number,
  size: number,
  signal?: AbortSignal,
): Promise<PatientPage> {
  const envelope = await apiRequest<PatientListItem[]>("/patients", {
    query: { page, size },
    signal,
  });
  const items = envelope.data ?? [];
  return { items, meta: envelope.meta ?? { page, size, total: items.length } };
}

export function getPatient(id: string, signal?: AbortSignal): Promise<Patient> {
  return apiFetch<Patient>(`/patients/${id}`, { signal });
}

export function createPatient(input: PatientInput): Promise<Patient> {
  return apiFetch<Patient>("/patients", { method: "POST", body: input });
}

export function updatePatient(id: string, input: PatientInput): Promise<Patient> {
  return apiFetch<Patient>(`/patients/${id}`, { method: "PUT", body: input });
}

export function deletePatient(id: string): Promise<PatientDeleteResponse> {
  return apiFetch<PatientDeleteResponse>(`/patients/${id}`, { method: "DELETE" });
}
