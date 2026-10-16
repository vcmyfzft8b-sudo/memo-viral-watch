// Records the ~20 s app demo creators play while filming (library → a note → flashcards → quiz → mind map → AI
// tutor) – one version per app language and device:  out/final/<Balkan|Slovenija>/Memo AI demo – <device>.mp4
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const HERE = path.dirname(new URL(import.meta.url).pathname);
const RAW = path.join(HERE, "out", "demos");
// The demo server runs a local Memo AI copy whose creator demo also shows the voice tutor tab (scripted, like the
// landing page): see README.
const APP = process.env.DEMO_APP ?? "http://localhost:3556";
const MEMO = process.env.DEMO_MEMO ?? path.join(process.env.HOME, "dev/Memo_AI-demo-tutor");
const LANGS = { hr: "Balkan", sl: "Slovenija" }; // Balkan pages use the Croatian (ijekavian) app
const DEVICES = { mac: "Mac", windows: "Windows", phone: "iPhone", android: "Android" };
const pick = process.argv.slice(2).find((a) => !a.startsWith("--"));
const devices = pick ? pick.split(",") : Object.keys(DEVICES);
const failed = [];

for (const lang of Object.keys(LANGS)) {
  for (const device of devices) {
    const file = path.join(RAW, `memo-ai-demo-tour-${device}-${lang}.mp4`);
    if (fs.existsSync(file) && !process.argv.includes("--redo")) continue;
    console.log(`=== ${lang} ${device}`);
    try {
      execFileSync(
        process.execPath,
        ["record.mjs", "--device", device, "--lang", lang, "--name", "tour", "--beats", "tour", "--out", RAW, "--no-warm", "--app", APP, "--memo", MEMO],
        { cwd: HERE, stdio: "inherit" },
      );
    } catch {
      failed.push(`${lang} ${device}`);
    }
  }
}

for (const [lang, market] of Object.entries(LANGS)) {
  const dir = path.join(HERE, "out", "final", market);
  fs.mkdirSync(dir, { recursive: true });
  for (const [device, label] of Object.entries(DEVICES)) {
    const src = path.join(RAW, `memo-ai-demo-tour-${device}-${lang}.mp4`);
    if (fs.existsSync(src)) fs.copyFileSync(src, path.join(dir, `Memo AI demo – ${label} (${market}).mp4`));
  }
}
console.log(failed.length ? `FAILED: ${failed.join(", ")}` : "no failures");
console.log("ALL-DONE");
