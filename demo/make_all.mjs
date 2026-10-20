// Records the app demo creators play while filming – one version per app language and device:
//   node make_all.mjs [devices] [--demo tour|notetaker] [--redo]
//   tour (default, ~20 s: library → a note → flashcards → quiz → mind map → AI tutor)
//        → out/final/<Balkan|Slovenija>/Memo AI demo – <device>.mp4
//   notetaker (~25 s, for the hand-written lecture scripts: record the lecture → notes → flashcard → quiz → test)
//        → out/final/<Balkan|Slovenija>/Memo AI demo zapiski – <device>.mp4
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const HERE = path.dirname(new URL(import.meta.url).pathname);
const RAW = path.join(HERE, "out", "demos");
// The demo server runs a local Memo AI copy whose creator demo also shows the voice tutor tab (scripted, like the
// landing page): see README. The notetaker demo runs on ~/dev/Memo_AI-demo-record (DEMO_APP / DEMO_MEMO, see README).
const APP = process.env.DEMO_APP ?? "http://localhost:3556";
const MEMO = process.env.DEMO_MEMO ?? path.join(process.env.HOME, "dev/Memo_AI-demo-tutor");
const LANGS = { hr: "Balkan", sl: "Slovenija" }; // Balkan pages use the Croatian (ijekavian) app
const DEVICES = { mac: "Mac", windows: "Windows", phone: "iPhone", android: "Android" };
const i = process.argv.indexOf("--demo");
const DEMO = i > -1 ? process.argv[i + 1] : "tour";
const LABEL = { tour: "Memo AI demo", notetaker: "Memo AI demo zapiski" }[DEMO];
// notetaker: /creator of the local copy whose record sheet is not staged (the production record screen, see README)
const PAGE_PATH = { tour: "/creator/college", notetaker: "/creator" }[DEMO];
if (!LABEL) throw new Error(`unknown --demo ${DEMO} (tour or notetaker)`);
const pick = process.argv.slice(2).find((a, n, all) => !a.startsWith("--") && all[n - 1] !== "--demo");
const devices = pick ? pick.split(",") : Object.keys(DEVICES);
const failed = [];

for (const lang of Object.keys(LANGS)) {
  for (const device of devices) {
    const file = path.join(RAW, `memo-ai-demo-${DEMO}-${device}-${lang}.mp4`);
    if (fs.existsSync(file) && !process.argv.includes("--redo")) continue;
    console.log(`=== ${lang} ${device}`);
    try {
      execFileSync(
        process.execPath,
        ["record.mjs", "--device", device, "--lang", lang, "--name", DEMO, "--beats", DEMO, "--out", RAW, "--no-warm", "--app", APP, "--memo", MEMO, "--path", PAGE_PATH],
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
    const src = path.join(RAW, `memo-ai-demo-${DEMO}-${device}-${lang}.mp4`);
    if (fs.existsSync(src)) fs.copyFileSync(src, path.join(dir, `${LABEL} – ${label} (${market}).mp4`));
  }
}
console.log(failed.length ? `FAILED: ${failed.join(", ")}` : "no failures");
console.log("ALL-DONE");
