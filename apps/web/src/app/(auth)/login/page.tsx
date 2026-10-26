import { LoginForm } from "@/components/auth/login-form";

export const metadata = { title: "Masuk" };

export default function LoginPage() {
  return (
    <>
      <h1 className="mb-4 text-lg font-semibold">Masuk</h1>
      <LoginForm />
    </>
  );
}
