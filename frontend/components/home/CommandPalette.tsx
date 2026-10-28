"use client";
import React, { useEffect, useState } from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Search, Home, BarChart2, Play, Terminal } from "lucide-react";

interface ShowcaseItem {
  id: string;
  title: string;
  repo: string;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [showcases, setShowcases] = useState<ShowcaseItem[]>([
    {
      id: "run_20261028_parse_duration",
      title: "parse_duration('1h30m') yields 90 instead of 5400",
      repo: "fast-utils/duration-parser",
    },
  ]);
  const router = useRouter();

  useEffect(() => {
    fetch("/replays/showcase.json")
      .then((res) => (res.ok ? res.json() : []))
      .then((items: ShowcaseItem[]) => {
        if (Array.isArray(items) && items.length > 0) {
          setShowcases(items);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  function navigate(path: string) {
    setOpen(false);
    router.push(path);
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4"
      style={{ background: "rgba(0, 0, 0, 0.65)", backdropFilter: "blur(4px)" }}
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-xl rounded-xl overflow-hidden shadow-2xl"
        style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <Command label="Command Palette" className="flex flex-col w-full">
          <div
            className="flex items-center px-4 py-3 gap-2"
            style={{ borderBottom: "1px solid var(--border)" }}
          >
            <Search size={18} style={{ color: "var(--text-muted)" }} />
            <Command.Input
              autoFocus
              placeholder="Type a command or search runs…"
              className="w-full bg-transparent text-sm outline-none font-sans"
              style={{ color: "var(--text)" }}
            />
            <kbd
              className="text-xs px-1.5 py-0.5 rounded font-mono"
              style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
            >
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2 text-sm">
            <Command.Empty
              className="p-4 text-center text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              No results found.
            </Command.Empty>

            <Command.Group heading="Navigation" className="px-2 py-1.5 text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
              <Command.Item
                onSelect={() => navigate("/")}
                className="flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-colors aria-selected:bg-[var(--border)]"
                style={{ color: "var(--text)" }}
              >
                <Home size={15} style={{ color: "var(--accent)" }} />
                <span>Home</span>
              </Command.Item>

              <Command.Item
                onSelect={() => navigate("/eval")}
                className="flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-colors aria-selected:bg-[var(--border)]"
                style={{ color: "var(--text)" }}
              >
                <BarChart2 size={15} style={{ color: "var(--accent)" }} />
                <span>Evaluation Benchmark (/eval)</span>
              </Command.Item>
            </Command.Group>

            <Command.Group heading="Showcase Runs" className="px-2 py-1.5 text-xs font-semibold mt-2" style={{ color: "var(--text-muted)" }}>
              {showcases.map((sc) => (
                <Command.Item
                  key={sc.id}
                  onSelect={() => navigate(`/run/${sc.id}`)}
                  className="flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors aria-selected:bg-[var(--border)]"
                  style={{ color: "var(--text)" }}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Play size={14} style={{ color: "var(--pass)" }} />
                    <span className="truncate">{sc.title}</span>
                  </div>
                  <span className="text-xs font-mono ml-2 flex-shrink-0" style={{ color: "var(--text-muted)" }}>
                    {sc.repo}
                  </span>
                </Command.Item>
              ))}
              <Command.Item
                onSelect={() => navigate("/run/run_20261028_parse_duration")}
                className="flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-colors aria-selected:bg-[var(--border)]"
                style={{ color: "var(--text)" }}
              >
                <Terminal size={14} style={{ color: "var(--accent)" }} />
                <span>Default Demo Run</span>
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}

export default CommandPalette;
