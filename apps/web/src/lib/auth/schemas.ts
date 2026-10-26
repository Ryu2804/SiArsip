import { z } from "zod";

// Limits mirror apps/api/app/schemas/user.py.
const email = z
  .string()
  .trim()
  .min(1, "Email wajib diisi.")
  .pipe(z.email("Format email tidak valid."));

const password = z
  .string()
  .min(8, "Kata sandi minimal 8 karakter.")
  .max(128, "Kata sandi maksimal 128 karakter.");

export const loginSchema = z.object({ email, password });
export type LoginValues = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Nama wajib diisi.")
    .max(255, "Nama maksimal 255 karakter."),
  email,
  password,
});
export type RegisterValues = z.infer<typeof registerSchema>;
