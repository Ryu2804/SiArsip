import { z } from "zod";

import type { Patient, PatientInput } from "@/lib/api/types";

// Rules mirror apps/api/app/schemas/patients.py. Every field is a string in the
// form; empty optional fields become null in toPatientInput.

function todayLocal(): string {
  return new Date().toLocaleDateString("sv-SE"); // YYYY-MM-DD in local time
}

export const patientSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Nama wajib diisi.")
    .max(100, "Nama maksimal 100 karakter."),
  mrn: z
    .string()
    .trim()
    .min(1, "No. RM wajib diisi.")
    .max(30, "No. RM maksimal 30 karakter.")
    .regex(/^[A-Za-z0-9/-]+$/, "No. RM hanya boleh huruf, angka, “/” dan “-”."),
  nik: z
    .string()
    .trim()
    .refine((v) => v === "" || /^\d{16}$/.test(v), "NIK harus 16 digit angka."),
  birth_date: z
    .string()
    .refine((v) => v === "" || v <= todayLocal(), "Tanggal lahir tidak boleh di masa depan."),
  diagnosis: z.string().trim().max(500, "Diagnosis maksimal 500 karakter."),
});

export type PatientFormValues = z.infer<typeof patientSchema>;

export const emptyPatientValues: PatientFormValues = {
  name: "",
  mrn: "",
  nik: "",
  birth_date: "",
  diagnosis: "",
};

export function toFormValues(patient: Patient): PatientFormValues {
  return {
    name: patient.name,
    mrn: patient.mrn,
    nik: patient.nik ?? "",
    birth_date: patient.birth_date ?? "",
    diagnosis: patient.diagnosis ?? "",
  };
}

export function toPatientInput(values: PatientFormValues): PatientInput {
  return {
    name: values.name,
    mrn: values.mrn,
    nik: values.nik || null,
    birth_date: values.birth_date || null,
    diagnosis: values.diagnosis || null,
  };
}
