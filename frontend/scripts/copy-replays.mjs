import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const srcDir = path.resolve(__dirname, "../../replays");
const destDir = path.resolve(__dirname, "../public/replays");

if (!fs.existsSync(destDir)) {
  fs.mkdirSync(destDir, { recursive: true });
}

if (fs.existsSync(srcDir)) {
  const files = fs.readdirSync(srcDir);
  for (const file of files) {
    if (file.endsWith(".jsonl") || file === "showcase.json") {
      const srcFile = path.join(srcDir, file);
      const destFile = path.join(destDir, file);
      fs.copyFileSync(srcFile, destFile);
      console.log(`[copy-replays] Copied ${file} to public/replays/`);

      if (file.endsWith(".jsonl")) {
        try {
          const content = fs.readFileSync(srcFile, "utf-8");
          const firstLine = content.split("\n").find((l) => l.trim().length > 0);
          if (firstLine) {
            const parsed = JSON.parse(firstLine);
            if (parsed.run_id && parsed.run_id !== file.replace(/\.jsonl$/, "")) {
              const aliasDest = path.join(destDir, `${parsed.run_id}.jsonl`);
              fs.copyFileSync(srcFile, aliasDest);
              console.log(`[copy-replays] Created alias ${parsed.run_id}.jsonl`);
            }
          }
        } catch {
          // ignore parse errors on alias creation
        }
      }
    }
  }
} else {
  console.warn(`[copy-replays] Source directory not found: ${srcDir}`);
}
