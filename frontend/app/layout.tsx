import type { Metadata } from "next";
import { Geist, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { CommandPalette } from "@/components/home/CommandPalette";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Fixie — Autonomous Bug Reproduction & Speculative Patch Engine",
  description:
    "Fixie reproduces bugs in an isolated sandbox, forks speculative patches, runs parallel verification, and delivers the winning patch with diff and PR.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${jetbrainsMono.variable} antialiased min-h-screen`}
        style={{
          backgroundColor: "var(--background)",
          color: "var(--text)",
          fontFamily: "var(--font-sans)",
        }}
      >
        <CommandPalette />
        {children}
      </body>
    </html>
  );
}
