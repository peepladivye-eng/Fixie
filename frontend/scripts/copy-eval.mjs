import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const srcFile = path.resolve(__dirname, "../../backend/eval/eval.json");
const destDir = path.resolve(__dirname, "../public");
const destFile = path.join(destDir, "eval.json");

if (!fs.existsSync(destDir)) {
  fs.mkdirSync(destDir, { recursive: true });
}

if (fs.existsSync(srcFile)) {
  fs.copyFileSync(srcFile, destFile);
  console.log(`[copy-eval] Copied ${srcFile} to ${destFile}`);
} else {
  console.warn(`[copy-eval] Source file not found: ${srcFile}`);
}
