"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { GlassCard } from "@glinui/ui";
import { LayoutDashboard, Settings, Sparkles, Target } from "lucide-react";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/onboarding", label: "Onboarding", icon: Sparkles },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/progress", label: "Progress", icon: Target },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-4 py-8 md:px-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-white/50">Guide Todoo</p>
          <h1 className="text-3xl font-semibold text-white">Liquid glass planner</h1>
        </div>
        <nav className="flex flex-wrap gap-2">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link key={href} href={href}>
                <GlassCard
                  size="sm"
                  className={`flex items-center gap-2 px-4 py-2 text-sm ${active ? "ring-1 ring-white/30" : "opacity-80"}`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </GlassCard>
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}
