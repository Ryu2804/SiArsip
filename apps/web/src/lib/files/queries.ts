"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { listPatientFiles } from "@/lib/api/files";
import type { FileCategory } from "@/lib/api/types";

const root = ["files"] as const;

export const fileKeys = {
  all: root,
  byPatient: (patientId: string) => [...root, "patient", patientId] as const,
  list: (patientId: string, page: number, size: number, category?: FileCategory) =>
    [...fileKeys.byPatient(patientId), page, size, category ?? "all"] as const,
  preview: (fileId: string) => [...root, "preview", fileId] as const,
};

export function usePatientFiles(
  patientId: string,
  page: number,
  size: number,
  category?: FileCategory,
) {
  return useQuery({
    queryKey: fileKeys.list(patientId, page, size, category),
    queryFn: ({ signal }) => listPatientFiles(patientId, page, size, category, signal),
    placeholderData: keepPreviousData,
  });
}
