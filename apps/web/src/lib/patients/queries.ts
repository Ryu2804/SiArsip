"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createPatient,
  deletePatient,
  getPatient,
  listPatients,
  updatePatient,
} from "@/lib/api/patients";
import type { PatientInput } from "@/lib/api/types";

export const patientKeys = {
  all: ["patients"] as const,
  lists: () => [...patientKeys.all, "list"] as const,
  list: (page: number, size: number) => [...patientKeys.lists(), page, size] as const,
  detail: (id: string) => [...patientKeys.all, "detail", id] as const,
};

export function usePatients(page: number, size: number) {
  return useQuery({
    queryKey: patientKeys.list(page, size),
    queryFn: ({ signal }) => listPatients(page, size, signal),
    placeholderData: keepPreviousData, // keep the old page visible while paging
  });
}

export function usePatient(id: string) {
  return useQuery({
    queryKey: patientKeys.detail(id),
    queryFn: ({ signal }) => getPatient(id, signal),
  });
}

export function useCreatePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PatientInput) => createPatient(input),
    onSuccess: (patient) => {
      queryClient.setQueryData(patientKeys.detail(patient.id), patient);
      return queryClient.invalidateQueries({ queryKey: patientKeys.lists() });
    },
  });
}

export function useUpdatePatient(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PatientInput) => updatePatient(id, input),
    onSuccess: (patient) => {
      queryClient.setQueryData(patientKeys.detail(id), patient);
      return queryClient.invalidateQueries({ queryKey: patientKeys.lists() });
    },
  });
}

export function useDeletePatient(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deletePatient(id),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: patientKeys.detail(id) });
      return queryClient.invalidateQueries({ queryKey: patientKeys.lists() });
    },
  });
}
