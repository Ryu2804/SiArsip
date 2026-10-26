"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { TextField } from "@/components/auth/text-field";
import { Button } from "@/components/ui/button";
import { register as registerUser } from "@/lib/api/auth";
import { ApiError, friendlyMessage } from "@/lib/api/errors";
import { registerSchema, type RegisterValues } from "@/lib/auth/schemas";

export function RegisterForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) });

  async function onSubmit(values: RegisterValues) {
    setFormError(null);
    try {
      await registerUser(values);
      toast.success("Pendaftaran berhasil. Silakan masuk.");
      router.replace("/login");
    } catch (error) {
      if (error instanceof ApiError && error.code === "email_already_registered") {
        setError("email", { message: "Email sudah terdaftar." });
      } else if (error instanceof ApiError && error.code === "username_already_taken") {
        setError("name", { message: "Nama sudah dipakai. Gunakan nama lain." });
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
        label="Nama"
        autoComplete="name"
        error={errors.name?.message}
        {...register("name")}
      />
      <TextField
        label="Email"
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...register("email")}
      />
      <TextField
        label="Kata sandi"
        type="password"
        autoComplete="new-password"
        error={errors.password?.message}
        {...register("password")}
      />
      <Button type="submit" size="lg" disabled={isSubmitting}>
        {isSubmitting ? "Memproses…" : "Daftar"}
      </Button>
      <p className="text-muted-foreground text-center text-sm">
        Sudah punya akun?{" "}
        <Link href="/login" className="text-foreground font-medium underline underline-offset-4">
          Masuk
        </Link>
      </p>
    </form>
  );
}
