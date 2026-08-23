export function PulseLoader({ label }: { label?: string }) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-12 text-text-muted">
        <svg
          width="120"
          height="32"
          viewBox="0 0 120 32"
          fill="none"
          className="text-accent"
        >
          <path
            d="M0 16 H40 L46 4 L54 28 L60 16 H120"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="animate-pulse-draw"
          />
        </svg>
        {label && <p className="text-sm font-sans">{label}</p>}
      </div>
    );
  }