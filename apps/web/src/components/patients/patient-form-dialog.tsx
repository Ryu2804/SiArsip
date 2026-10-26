"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { TextAreaField, TextField } from "@/components/form/text-field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApiError, friendlyMessage } from "@/lib/api/errors";
import type { Patient } from "@/lib/api/types";
import {
  emptyPatientValues,
  patientSchema,
  toFormValues,
  toPatientInput,
  type PatientFormValues,
} from "@/lib/patients/schemas";
import { useCreatePatient, useUpdatePatient } from "@/lib/patients/queries";

interface PatientFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present when editing; absent when creating. */
  patient?: Patient;
  onSaved?: (patient: Patient) => void;
}

export function PatientFormDialog({
  open,
  onOpenChange,
  patient,
  onSaved,
}: PatientFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{patient ? "Ubah data pasien" : "Tambah pasien"}</DialogTitle>
          <DialogDescription>
            Kolom bertanda * wajib diisi. NIK dan diagnosis bersifat opsional.
          </DialogDescription>
        </DialogHeader>
        {/* Mounted only while open, so every opening starts from fresh values. */}
        <PatientForm
          patient={patient}
          onCancel={() => onOpenChange(false)}
          onSaved={(saved) => {
            onOpenChange(false);
            onSaved?.(saved);
          }}
        />
      </DialogContent>
    </Dialog>
  );
}

function PatientForm({
  patient,
  onCancel,
  onSaved,
}: {
  patient?: Patient;
  onCancel: () => void;
  onSaved: (patient: Patient) => void;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const create = useCreatePatient();
  const update = useUpdatePatient(patient?.id ?? "");

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<PatientFormValues>({
    resolver: zodResolver(patientSchema),
    defaultValues: patient ? toFormValues(patient) : emptyPatientValues,
  });

  async function onSubmit(values: PatientFormValues) {
    setFormError(null);
    const input = toPatientInput(values);
    try {
      const saved = patient
        ? await update.mutateAsync(input)
        : await create.mutateAsync(input);
      onSaved(saved);
    } catch (error) {
      // The backend's duplicate-MRN error is a plain 400; no other 400 comes
      // from this endpoint, so treat it as "No. RM already used".
      if (error instanceof ApiError && error.status === 400) {
        setError("mrn", { message: "No. RM sudah terdaftar." });
      } else {
        setFormError(friendlyMessage(error));
      }
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      {formError && (
        <p role="alert" className="bg-destructive/10 text-destructive rounded-lg px-3 py-2 text-sm">
          {formError}
        </p>
      )}
      <TextField
        label="No. RM *"
        autoComplete="off"
        error={errors.mrn?.message}
        {...register("mrn")}
      />
      <TextField
        label="Nama *"
        autoComplete="off"
        error={errors.name?.message}
        {...register("name")}
      />
      <TextField
        label="NIK"
        inputMode="numeric"
        maxLength={16}
        autoComplete="off"
        hint="16 digit angka."
        error={errors.nik?.message}
        {...register("nik")}
      />
      <TextField
        label="Tanggal lahir"
        type="date"
        error={errors.birth_date?.message}
        {...register("birth_date")}
      />
      <TextAreaField
        label="Diagnosis"
        error={errors.diagnosis?.message}
        {...register("diagnosis")}
      />
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Batal
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Menyimpan…" : "Simpan"}
        </Button>
      </DialogFooter>
    </form>
  );
}
