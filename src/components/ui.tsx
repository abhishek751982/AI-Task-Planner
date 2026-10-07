"use client";

import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { Loader2 } from "lucide-react";
import {
  useCallback,
  useEffect,
  useRef,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";
import { spring } from "@/components/motion";

/* ── Card ──────────────────────────────────────────────────
   A frosted panel. `spotlight` makes a soft light follow the
   cursor across the surface; `lift` raises it on hover.       */

export function Card({
  children,
  className = "",
  hero = false,
  spotlight = true,
  lift = false,
}: {
  children: ReactNode;
  className?: string;
  hero?: boolean;
  spotlight?: boolean;
  lift?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  const onMove = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      if (!spotlight) return;
      const el = ref.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      el.style.setProperty("--mx", `${e.clientX - r.left}px`);
      el.style.setProperty("--my", `${e.clientY - r.top}px`);
    },
    [spotlight],
  );

  const classes = [
    "card",
    hero ? "card--hero" : "",
    spotlight ? "card--spot" : "",
    lift ? "card--lift" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div ref={ref} className={classes} onPointerMove={onMove}>
      {children}
    </div>
  );
}

/* ── Buttons ───────────────────────────────────────────── */

type BtnProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onAnimationStart" | "onDragStart" | "onDragEnd" | "onDrag"> & {
  loading?: boolean;
};

/** Primary action. Drifts a few pixels toward the cursor — magnetic. */
export function Btn({ className = "", children, loading, disabled, ...props }: BtnProps) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLButtonElement>(null);
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const x = useSpring(mx, spring);
  const y = useSpring(my, spring);

  function onMove(e: ReactPointerEvent<HTMLButtonElement>) {
    if (reduced || disabled || loading) return;
    const r = ref.current?.getBoundingClientRect();
    if (!r) return;
    mx.set((e.clientX - (r.left + r.width / 2)) * 0.22);
    my.set((e.clientY - (r.top + r.height / 2)) * 0.28);
  }

  function reset() {
    mx.set(0);
    my.set(0);
  }

  return (
    <motion.button
      ref={ref}
      className={`btn ${className}`.trim()}
      style={{ x, y }}
      whileTap={reduced ? undefined : { scale: 0.96 }}
      onPointerMove={onMove}
      onPointerLeave={reset}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 spin" /> : null}
      {children}
    </motion.button>
  );
}

export function BtnGhost({ className = "", children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className={`btn-ghost ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}

/* ── Form ──────────────────────────────────────────────── */

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`input ${className}`.trim()} {...props} />;
}

export function Select({ className = "", children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={`input select ${className}`.trim()} {...props}>
      {children}
    </select>
  );
}

/* ── Data display ──────────────────────────────────────── */

/** Hairline progress bar. */
export function Bar({ value }: { value: number }) {
  const reduced = useReducedMotion();
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <motion.div
        className="bar-fill"
        initial={{ width: reduced ? `${pct}%` : 0 }}
        animate={{ width: `${pct}%` }}
        transition={reduced ? { duration: 0 } : { duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
      />
    </div>
  );
}

/**
 * Circular progress. The stroke draws itself in on mount, which is the
 * single most satisfying moment on the dashboard.
 */
export function Ring({ value, size = 168, stroke = 6, children }: { value: number; size?: number; stroke?: number; children?: ReactNode }) {
  const reduced = useReducedMotion();
  const pct = Math.min(100, Math.max(0, value));
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const progress = useMotionValue(reduced ? pct : 0);
  const eased = useSpring(progress, { stiffness: 42, damping: 18, mass: 1 });
  const offset = useTransform(eased, (v) => circumference - (v / 100) * circumference);

  useEffect(() => {
    progress.set(pct);
  }, [pct, progress]);

  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--ring-track)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          style={{ strokeDashoffset: offset }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">{children}</div>
    </div>
  );
}

export function Pill({
  children,
  tone = "default",
  pulse = false,
}: {
  children: ReactNode;
  tone?: "default" | "ok" | "warn";
  pulse?: boolean;
}) {
  const toneClass = tone === "ok" ? "pill--ok" : tone === "warn" ? "pill--warn" : "";
  return (
    <span className={`pill ${toneClass}`.trim()}>
      {pulse ? <span className="pill-dot" aria-hidden /> : null}
      {children}
    </span>
  );
}

/** Small mono label above a block of content. */
export function Eyebrow({ children, rule = true }: { children: ReactNode; rule?: boolean }) {
  return (
    <span className="mono eyebrow">
      {rule ? <i className="eyebrow-rule" aria-hidden /> : null}
      {children}
    </span>
  );
}

/** Card header: icon-free, mono label on the left, optional slot on the right. */
export function CardHead({ label, title, aside }: { label: string; title: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <Eyebrow>{label}</Eyebrow>
        <h2 className="display-sm mt-2.5">{title}</h2>
      </div>
      {aside ? <div className="flex-none pt-1">{aside}</div> : null}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`.trim()} />;
}

export function InlineLoader({ label = "Thinking" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2.5 py-10 justify-center">
      <Loader2 className="h-4 w-4 spin accent" />
      <span className="mono ink-3">{label}…</span>
    </div>
  );
}
