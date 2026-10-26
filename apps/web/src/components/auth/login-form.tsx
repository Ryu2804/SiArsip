"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { TextField } from "@/components/auth/text-field";
import { Button } from "@/components/ui/button";
import { login } from "@/lib/api/auth";
import { ApiError, friendlyMessage } from "@/lib/api/errors";
import { loginSchema, type LoginValues } from "@/lib/auth/schemas";

export function LoginForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginValues) {
    setFormError(null);
    try {
      await login(values);
      router.replace("/patients");
    } catch (error) {
      // A 401 here means wrong credentials, not an expired session.
      setFormError(
        error instanceof ApiError && error.status === 401
          ? "Email atau kata sandi salah."
          : friendlyMessage(error),
      );
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
        label="Email"
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...register("email")}
      />
      <TextField
        label="Kata sandi"
        type="password"
        autoComplete="current-password"
        error={errors.password?.message}
        {...register("password")}
      />
      <Button type="submit" size="lg" disabled={isSubmitting}>
        {isSubmitting ? "Memproses…" : "Masuk"}
      </Button>
      <p className="text-muted-foreground text-center text-sm">
        Belum punya akun?{" "}
        <Link href="/register" className="text-foreground font-medium underline underline-offset-4">
          Daftar
        </Link>
      </p>
    </form>
  );
}
