"use client";

import { motion, useReducedMotion, type HTMLMotionProps, type Transition } from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";

/** A soft, slightly overshooting spring — the "satisfying" curve. */
export const spring: Transition = { type: "spring", stiffness: 190, damping: 24, mass: 0.9 };

/** Editorial easing for opacity/position fades. */
export const glide: Transition = { duration: 0.6, ease: [0.16, 1, 0.3, 1] };

type DivProps = HTMLMotionProps<"div"> & { children: ReactNode };

/** Parent that releases its children one after another. */
export function Stagger({ children, className, delay = 0, gap = 0.07, ...props }: DivProps & { delay?: number; gap?: number }) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="show"
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: reduced ? 0 : gap, delayChildren: reduced ? 0 : delay } },
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

/**
 * Child of <Stagger>. Rises and settles.
 *
 * Deliberately no `filter` here: framer leaves an inline `blur(0px)` behind,
 * and any non-`none` filter makes this element a backdrop root — which would
 * flatten the `backdrop-filter` frosting on every Card inside it.
 */
export function Item({ children, className, ...props }: DivProps) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      className={className}
      variants={{
        hidden: reduced ? { opacity: 0 } : { opacity: 0, y: 20, scale: 0.985 },
        show: { opacity: 1, y: 0, scale: 1, transition: reduced ? { duration: 0.15 } : glide },
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

/**
 * Simple entrance for standalone text blocks. This one *does* focus-in from
 * a blur — only use it where no frosted Card lives inside (see Item).
 */
export function FadeIn({ children, className, delay = 0, ...props }: DivProps & { delay?: number }) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduced ? { opacity: 0 } : { opacity: 0, y: 14, filter: "blur(5px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={reduced ? { duration: 0.15 } : { ...glide, delay }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

/**
 * Counts from 0 to `value`. Uses an eased ramp rather than a linear one so
 * the number decelerates into place.
 */
export function CountUp({ value, suffix = "", duration = 1100 }: { value: number; suffix?: string; duration?: number }) {
  const reduced = useReducedMotion();
  const [shown, setShown] = useState(reduced ? value : 0);
  const frame = useRef(0);

  useEffect(() => {
    if (reduced) {
      setShown(value);
      return;
    }
    const from = 0;
    const start = performance.now();

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(Math.round(from + (value - from) * eased));
      if (t < 1) frame.current = requestAnimationFrame(tick);
    };

    frame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame.current);
  }, [value, duration, reduced]);

  return (
    <>
      {shown}
      {suffix}
    </>
  );
}
