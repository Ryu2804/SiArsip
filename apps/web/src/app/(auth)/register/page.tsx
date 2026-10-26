import { RegisterForm } from "@/components/auth/register-form";

export const metadata = { title: "Daftar" };

export default function RegisterPage() {
  return (
    <>
      <h1 className="mb-4 text-lg font-semibold">Buat akun</h1>
      <RegisterForm />
    </>
  );
}
