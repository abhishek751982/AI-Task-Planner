"use client";

import { useEffect, useRef } from "react";

const COUNT = 18;

type Mote = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  /** Depth 0..1 — drives size, opacity and parallax strength. */
  z: number;
  phase: number;
};

type Ripple = { x: number; y: number; strength: number; age: number };

function isInteractive(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  return !!target.closest(
    "a, button, input, select, textarea, label, [role='button'], [role='link'], [contenteditable='true']",
  );
}

/**
 * Slow-drifting dust. Deliberately sparse and low-contrast: it should read
 * as depth in the room, not as an effect you notice.
 */
export function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let w = 0;
    let h = 0;
    let raf = 0;
    let t = 0;
    let visible = !document.hidden;
    let tint = "127, 201, 174";

    const motes: Mote[] = [];
    let ripples: Ripple[] = [];
    const pointer = { x: 0, y: 0, tx: 0, ty: 0 };

    const readTint = () => {
      const raw = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
      const m = /^#([0-9a-f]{6})$/i.exec(raw);
      if (!m) return;
      const n = parseInt(m[1]!, 16);
      tint = `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`;
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const seed = () => {
      motes.length = 0;
      for (let i = 0; i < COUNT; i++) {
        const z = Math.random();
        motes.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.09,
          vy: -0.02 - Math.random() * 0.05,
          r: 1 + z * 2.6,
          z,
          phase: Math.random() * Math.PI * 2,
        });
      }
    };

    const tick = () => {
      raf = requestAnimationFrame(tick);
      if (!visible) return;
      t += 1;

      // Pointer eases toward its target so parallax never feels twitchy.
      pointer.x += (pointer.tx - pointer.x) * 0.045;
      pointer.y += (pointer.ty - pointer.y) * 0.045;

      ctx.clearRect(0, 0, w, h);

      ripples = ripples.filter((r) => {
        r.age += 1;
        r.strength *= 0.93;
        return r.age < 44 && r.strength > 0.3;
      });

      for (const p of motes) {
        for (const r of ripples) {
          const dx = p.x - r.x;
          const dy = p.y - r.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 140 && dist > 1) {
            const push = (r.strength * (140 - dist)) / 140;
            p.vx += (dx / dist) * push * 0.03;
            p.vy += (dy / dist) * push * 0.03;
          }
        }

        p.x += p.vx + Math.sin(t * 0.004 + p.phase) * 0.08;
        p.y += p.vy;
        p.vx *= 0.994;
        p.vy = p.vy * 0.994 - 0.00012;

        if (p.y < -20) {
          p.y = h + 20;
          p.x = Math.random() * w;
          p.vy = -0.02 - Math.random() * 0.05;
        }
        if (p.x < -20) p.x = w + 20;
        else if (p.x > w + 20) p.x = -20;

        // Nearer motes shift more with the cursor.
        const par = (p.z - 0.5) * 26;
        const px = p.x + pointer.x * par;
        const py = p.y + pointer.y * par;

        const alpha = 0.06 + p.z * 0.16;
        const glow = ctx.createRadialGradient(px, py, 0, px, py, p.r * 4);
        glow.addColorStop(0, `rgba(${tint}, ${alpha})`);
        glow.addColorStop(1, `rgba(${tint}, 0)`);
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(px, py, p.r * 4, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    const onPointerMove = (e: PointerEvent) => {
      pointer.tx = (e.clientX / w) * 2 - 1;
      pointer.ty = (e.clientY / h) * 2 - 1;
    };

    const onClick = (e: MouseEvent) => {
      if (isInteractive(e.target)) return;
      ripples.push({ x: e.clientX, y: e.clientY, strength: 3.5, age: 0 });
    };

    const onVisibility = () => {
      visible = !document.hidden;
    };

    readTint();
    resize();
    seed();

    const themeWatcher = new MutationObserver(readTint);
    themeWatcher.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    document.addEventListener("click", onClick);
    document.addEventListener("visibilitychange", onVisibility);
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      themeWatcher.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("click", onClick);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return <canvas ref={canvasRef} className="motes" aria-hidden />;
}
