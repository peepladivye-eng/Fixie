"use client";
import { NotFoundState } from "@/components/states";

export default function NotFound() {
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-8"
      style={{ background: "var(--background)", color: "var(--text)" }}
    >
      <NotFoundState />
    </div>
  );
}
