// Simple CSS architecture diagram — no library dependency
export default function ArchDiagram() {
  const boxes: { label: string; sub?: string; color: string }[] = [
    { label: "Browser", sub: "Next.js SSE client", color: "var(--border)" },
    { label: "FastAPI", sub: "SSE endpoint", color: "var(--border)" },
    { label: "Token Factory", sub: "LLM inference", color: "var(--border)" },
    { label: "Sandboxes", sub: "VM fork + test", color: "var(--border)" },
  ];

  return (
    <div className="space-y-4">
      {/* Diagram row */}
      <div
        className="flex flex-wrap items-center gap-2 p-4 rounded-xl overflow-x-auto"
        style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
        role="img"
        aria-label="Architecture: Browser connects to FastAPI over SSE, which calls Token Factory for LLM inference and Sandboxes for VM isolation and forking."
      >
        {boxes.map((box, i) => (
          <div key={box.label} className="flex items-center gap-2">
            <div
              className="flex flex-col items-center justify-center px-4 py-3 rounded-lg text-center flex-shrink-0 min-w-[110px]"
              style={{ background: "var(--background)", border: `1px solid ${box.color}` }}
            >
              <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                {box.label}
              </span>
              {box.sub && (
                <span className="text-xs mt-0.5 font-mono" style={{ color: "var(--text-muted)" }}>
                  {box.sub}
                </span>
              )}
            </div>
            {i < boxes.length - 1 && (
              <span className="text-lg flex-shrink-0" style={{ color: "var(--accent)" }} aria-hidden="true">
                →
              </span>
            )}
          </div>
        ))}

        {/* Fork annotation */}
        <div
          className="ml-2 px-3 py-1.5 rounded-lg text-xs font-mono flex-shrink-0"
          style={{ background: "var(--surface)", border: "1px dashed var(--accent)", color: "var(--accent)" }}
        >
          × K branches in parallel
        </div>
      </div>

      {/* Key insight */}
      <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
        State = a sandbox image ID; a fork is just starting from the same ID.
        Each candidate branch runs identical tests in its own container;
        the deterministic scorer picks the winner without any model call.
      </p>
    </div>
  );
}
