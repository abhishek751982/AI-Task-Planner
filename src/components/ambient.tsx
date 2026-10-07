/**
 * Atmosphere layers that sit behind everything: three very slow aurora
 * blooms, plus an animated film grain that keeps the flat colour fields
 * from looking digital.
 */
export function AmbientBackground() {
  return (
    <>
      <div className="atmos" aria-hidden>
        <div className="aurora aurora-1" />
        <div className="aurora aurora-2" />
        <div className="aurora aurora-3" />
      </div>
      <div className="grain" aria-hidden />
    </>
  );
}

/** Concentric-rings mark used wherever a panel has nothing to show yet. */
export function EmptyIllustration() {
  return (
    <svg className="empty-art" viewBox="0 0 88 88" fill="none" aria-hidden>
      <circle cx="44" cy="44" r="34" stroke="currentColor" strokeOpacity="0.14" strokeWidth="1" />
      <circle cx="44" cy="44" r="23" stroke="currentColor" strokeOpacity="0.22" strokeWidth="1" />
      <circle
        cx="44"
        cy="44"
        r="34"
        stroke="currentColor"
        strokeOpacity="0.55"
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeDasharray="30 184"
        transform="rotate(-90 44 44)"
      />
      <circle cx="44" cy="44" r="4" fill="currentColor" fillOpacity="0.4" />
    </svg>
  );
}
