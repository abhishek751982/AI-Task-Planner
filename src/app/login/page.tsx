import { AuthForm } from "@/components/auth-form";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ created?: string }>;
}) {
  const params = await searchParams;
  return <AuthForm mode="login" notice={params.created ? "Account created. Sign in to continue." : undefined} />;
}
