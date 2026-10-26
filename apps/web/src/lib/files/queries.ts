// Query keys for patient files. The list query itself arrives with SIA-111; the
// key lives here now so uploads can already invalidate it.
export const fileKeys = {
  all: ["files"] as const,
  byPatient: (patientId: string) => [...fileKeys.all, "patient", patientId] as const,
};
