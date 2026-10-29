// Static table: how Fixie uses Nebius + NVIDIA
export default function AboutTable() {
  const rows = [
    {
      step: "Triage",
      nvidia: "Nemotron 3 Nano",
      nebius: "Token Factory",
      why: "Cheap high-volume JSON ranking of search results and issue metadata.",
    },
    {
      step: "Repro + patch",
      nvidia: "Nemotron 3 Super",
      nebius: "Token Factory (tool calling)",
      why: "Reliable tool calls at low cost — executes repro scripts inside the sandbox.",
    },
    {
      step: "Diagnose",
      nvidia: "Nemotron 3 Ultra",
      nebius: "Token Factory",
      why: "Hard reasoning invoked only when all branches fail; highest accuracy tier.",
    },
    {
      step: "Run, test, fork",
      nvidia: "none",
      nebius: "Token Factory Sandboxes",
      why: "VM isolation; checkpoint + fork = branch-and-select at container layer.",
    },
  ];

  return (
    <div>
      <div className="overflow-x-auto rounded-xl" style={{ border: "1px solid var(--border)" }}>
        <table className="w-full text-sm text-left">
          <thead style={{ background: "var(--background)", color: "var(--text-muted)" }}>
            <tr>
              {["Step", "NVIDIA model", "Nebius service", "Why"].map((h) => (
                <th key={h} className="px-4 py-3 text-xs font-mono uppercase tracking-wide whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody style={{ background: "var(--surface)" }}>
            {rows.map((r) => (
              <tr key={r.step} style={{ borderTop: "1px solid var(--border)" }}>
                <td className="px-4 py-3 font-semibold whitespace-nowrap" style={{ color: "var(--accent)" }}>
                  {r.step}
                </td>
                <td className="px-4 py-3 font-mono text-xs whitespace-nowrap" style={{ color: "var(--text)" }}>
                  {r.nvidia}
                </td>
                <td className="px-4 py-3 font-mono text-xs whitespace-nowrap" style={{ color: "var(--badge-blue)" }}>
                  {r.nebius}
                </td>
                <td className="px-4 py-3 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {r.why}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs italic" style={{ color: "var(--text-muted)" }}>
        Model names shown are the intended tiers; each recorded run lists the exact models it used.
      </p>
    </div>
  );
}
