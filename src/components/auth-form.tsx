"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { ThemeToggle } from "@/components/app-shell";
import { Btn, Card, Eyebrow, Field, Input } from "@/components/ui";
import { api } from "@/lib/api";

const points = [
  ["01", "Your tasks stay on your account"],
  ["02", "Plans follow your hours, not a generic list"],
  ["03", "Memory and scores belong only to you"],
];

export function AuthForm({ mode, notice }: { mode: "login" | "register"; notice?: string }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "register") {
        await api.register({ email, password, name });
        router.replace("/signin?created=1");
        return;
      }
      await api.login({ email, password });
      router.replace("/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in");
    } finally {
      setBusy(false);
    }
  }

  const creating = mode === "register";

  return (
    <div className="auth-stage">
      <header className="auth-bar">
        <div className="auth-brand">
          <span className="mark-glyph" aria-hidden>
            gt
          </span>
          <span className="auth-brand-name">Guide Todoo</span>
        </div>
        <ThemeToggle compact />
      </header>

      <div className="auth-body">
        <div className="auth-layout">
          <section className="auth-copy">
            <Eyebrow>Personal planner</Eyebrow>
            <h1 className="display mt-5">
              A calmer way to <em>plan</em>
            </h1>
            <p className="lede mt-5">
              One account, one day at a time. The planner learns your hours and keeps everyone else’s work out of the way.
            </p>
            <ul className="auth-points">
              {points.map(([index, label]) => (
                <li key={index}>
                  <i>{index}</i>
                  <span>{label}</span>
                </li>
              ))}
            </ul>
          </section>

          <Card className="auth-card" hero spotlight>
            <div className="auth-switch">
              <Link href="/signup" aria-current={creating ? "page" : undefined}>
                Create account
              </Link>
              <Link href="/signin" aria-current={creating ? undefined : "page"}>
                Sign in
              </Link>
            </div>

            <Eyebrow>{creating ? "New here" : "Welcome back"}</Eyebrow>
            <h2 className="display-sm mt-3">{creating ? "Start your own plan" : "Pick up where you left off"}</h2>
            <p className="lede mt-3">
              {notice ??
                (creating
                  ? "Name, email, and a password. That’s the whole setup."
                  : "Use the email you signed up with.")}
            </p>

            <form className="auth-form mt-6" onSubmit={submit}>
              {creating ? (
                <Field label="Name">
                  <Input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" placeholder="Your name" />
                </Field>
              ) : null}
              <Field label="Email">
                <Input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="you@email.com"
                />
              </Field>
              <Field label="Password">
                <span className="password-field">
                  <Input
                    type={showPassword ? "text" : "password"}
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete={creating ? "new-password" : "current-password"}
                    placeholder="At least 8 characters"
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    aria-pressed={showPassword}
                    onClick={() => setShowPassword((open) => !open)}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" strokeWidth={1.7} /> : <Eye className="h-4 w-4" strokeWidth={1.7} />}
                  </button>
                </span>
              </Field>
              {error ? (
                <p className="auth-error" role="alert">
                  {error}
                </p>
              ) : null}
              <Btn type="submit" loading={busy}>
                {creating ? "Create account" : "Sign in"}
              </Btn>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
