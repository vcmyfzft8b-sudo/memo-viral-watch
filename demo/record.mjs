// Records the Memo AI app demo (the offline /creator/college demo of the real app) as a video creators can play
// on their laptop or phone and film. See README.md.
//
//   node record.mjs --device mac|windows|phone|short --lang sl|hr|sr|bs [--app http://localhost:3555] [--debug]
//        --beats upload,record,cards,test,quiz,more [--name top5]   (see BEATS)
import { chromium } from "playwright";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const HERE = path.dirname(new URL(import.meta.url).pathname);
const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
};
const DEVICE = { laptop: "mac" }[arg("device", "mac")] ?? arg("device", "mac");
const LANG = arg("lang", "sl");
const APP = arg("app", "http://localhost:3555");
const MEMO = arg("memo", path.join(os.homedir(), "dev/Memo_AI"));
const DEBUG = process.argv.includes("--debug");
const OUT = arg("out", path.join(HERE, "out"));
const NAME = arg("name", "demo");
const FRAMES = path.join(HERE, "frames", `${NAME}-${DEVICE}-${LANG}`);
const SHORT = DEVICE === "short";
const ANDROID = DEVICE === "android";
const PHONE = DEVICE === "phone" || ANDROID || SHORT;
/** Playback speed of the finished video (the short plays a bit faster, like an edited insert). */
const SPEED = Number(arg("speed", 1));

// Screen = what the video shows. The page gets the screen minus the fake browser bars drawn around it.
//  The flashcard is a 5:3 box as tall as the window allows, so the laptops use their real full heights.
const SCREEN = {
  mac: { w: 1728, h: 1117, top: 44, bottom: 0, dsf: 2, outW: 1920 }, // MacBook Pro 16", default scaling
  windows: { w: 1920, h: 1080, top: 80, bottom: 0, dsf: 1, outW: 1920 }, // 1080p laptop at 100 %
  phone: { w: 393, h: 852, top: 54, bottom: 78, dsf: 3, outW: 1080 }, // iPhone 15/16, Safari
  android: { w: 360, h: 780, top: 84, bottom: 18, dsf: 3, outW: 1080 }, // Samsung Galaxy S, Chrome
}[DEVICE];
if (!SCREEN) throw new Error(`unknown --device ${DEVICE} (mac, windows, phone or android)`);
const VIEW = { width: SCREEN.w, height: SCREEN.h - SCREEN.top - SCREEN.bottom };

// ---------------------------------------------------------------- app texts (the app's own translations)
function loadMessages(lang) {
  const src = fs.readFileSync(path.join(MEMO, "src/lib/i18n/messages", `${lang}.ts`), "utf8");
  const out = {};
  for (const [, k, v] of src.matchAll(/"([\w.-]+)":\s*"((?:[^"\\]|\\.)*)"/g)) out[k] = JSON.parse(`"${v}"`);
  return out;
}
function loadQuizAnswers(lang) {
  const src = fs.readFileSync(path.join(MEMO, "src/lib/creator-demo/locales", `${lang}.ts`), "utf8");
  const out = new Map();
  const re = /prompt:\s*"((?:[^"\\]|\\.)*)",\s*options:\s*\[([\s\S]*?)\],\s*correctOptionIdx:\s*(\d+)/g;
  for (const [, prompt, opts, idx] of src.matchAll(re)) {
    const options = [...opts.matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((m) => JSON.parse(`"${m[1]}"`));
    out.set(JSON.parse(`"${prompt}"`), { options, correct: options[Number(idx)] });
  }
  return out;
}
/** Practice-test question → a short version of its model answer (what a student would type). */
function loadPracticeAnswers(lang) {
  const src = fs.readFileSync(path.join(MEMO, "src/lib/creator-demo/locales", `${lang}.ts`), "utf8");
  const out = new Map();
  const re = /prompt:\s*"((?:[^"\\]|\\.)*)",\s*answerGuide:[\s\S]*?expectedAnswer:\s*"((?:[^"\\]|\\.)*)"/g;
  for (const [, prompt, answer] of src.matchAll(re)) {
    const full = JSON.parse(`"${answer}"`);
    const cut = full.slice(40).search(/[,.;]/);
    out.set(JSON.parse(`"${prompt}"`), cut < 0 ? full : full.slice(0, 40 + cut) + ".");
  }
  return out;
}
const M = loadMessages(LANG);
const PRACTICE = loadPracticeAnswers(LANG);
const QUIZ = loadQuizAnswers(LANG);

// ---------------------------------------------------------------- page helpers
const MAC_CURSOR = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="24" viewBox="0 0 26 34"><path d="M2 2 L2 27 L8.2 21.2 L12.4 31 L16.6 29.2 L12.5 19.6 L21 19.6 Z" fill="#000" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>`;
const WINDOWS_CURSOR = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="21" viewBox="0 0 22 32"><path d="M1.5 1.5 L1.5 25 L7 19.8 L11 28.6 L14.4 27.1 L10.5 18.5 L18 18.5 Z" fill="#fff" stroke="#000" stroke-width="1.4" stroke-linejoin="miter"/></svg>`;
const CURSOR_SVG = DEVICE === "windows" ? WINDOWS_CURSOR : MAC_CURSOR;

function initScript({ cursorSvg, laptop }) {
  const style = document.createElement("style");
  // The dev-server badge and toasts never belong in a recording; the real cursor is drawn by #demo-cursor.
  style.textContent = `nextjs-portal{display:none!important}
    #demo-cursor{position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;will-change:transform;
      transition:none;filter:drop-shadow(0 1px 2px rgba(0,0,0,.35))}
    #demo-cursor svg{display:block;transform-origin:1px 1px;transition:transform .09s ease}
    #demo-cursor.down svg{transform:scale(.82)}
    html{scrollbar-width:none} ::-webkit-scrollbar{display:none}
    /* laptops: the flashcard may use the free height under it (the app caps it at 22rem) */
    @media (min-width: 1100px){.memo-note-screen[data-note-tab="flashcards"] .lecture-flashcard-stage{max-height:27rem!important}}`;
  // Log every sound the page plays (the voice tutor's recordings), so the video gets the same audio track.
  if (!window.__demoAudio) {
    window.__demoAudio = [];
    const play = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function (...args) {
      const el = this;
      if (!el.__demoId) {
        el.__demoId = Math.random().toString(36).slice(2);
        for (const ev of ["pause", "ended"])
          el.addEventListener(ev, () => window.__demoAudio.push({ type: "stop", id: el.__demoId, t: Date.now() }));
      }
      (window.__demoEls ??= {})[el.__demoId] = el;
      window.__demoAudio.push({ type: "play", id: el.__demoId, src: el.src, t: Date.now(), offset: el.currentTime, muted: el.muted, volume: el.volume });
      return play.apply(this, args);
    };
  }
  const mount = () => {
    document.head.appendChild(style);
    if (!laptop || document.getElementById("demo-cursor")) return;
    const c = document.createElement("div");
    c.id = "demo-cursor";
    c.innerHTML = cursorSvg;
    const p = JSON.parse(sessionStorage.getItem("demo-cursor") || "[720,520]");
    c.style.transform = `translate(${p[0]}px,${p[1]}px)`;
    c.dataset.x = p[0];
    c.dataset.y = p[1];
    document.body.appendChild(c);
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
  // Keep the cursor alive across client-side navigations that re-render <body> children.
  new MutationObserver(() => {
    if (laptop && document.body && !document.getElementById("demo-cursor")) mount();
  }).observe(document, { childList: true, subtree: true });
}

let page;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const vis = (loc) => loc.filter({ visible: true }).first();
const byText = (text, exact = true) => vis(page.getByText(text, { exact }));
const iconButton = (icon) => vis(page.locator(`button:has(:text-is("${icon}")), a:has(:text-is("${icon}"))`));
let step = 0;
let chapterClock = null;
const chapters = [];
/** Marks where a part of the demo starts, so creators know where to film. */
function chapter(name) {
  if (chapterClock) chapters.push([(Date.now() - chapterClock) / 1000, name]);
}
/** Waiting screens (uploading, "making cards…") play `factor`× faster in the video, so they read but don't drag. */
const warps = [];
async function fast(fn, factor = 3) {
  const a = chapterClock ? (Date.now() - chapterClock) / 1000 : null;
  await fn();
  if (a != null) warps.push([a, (Date.now() - chapterClock) / 1000, factor]);
}
/** Recording time → video time. */
function videoTime(t) {
  let out = t;
  for (const [a, b, f] of warps) out -= (Math.min(Math.max(t, a), b) - a) * (1 - 1 / f);
  return out / SPEED;
}
async function snap(name) {
  if (DEBUG) await page.screenshot({ path: path.join(OUT, `debug-${DEVICE}-${LANG}-${String(step++).padStart(2, "0")}-${name}.png`) });
}

const rand = (a, b) => a + Math.random() * (b - a);

/** Moves the drawn cursor like a hand on a trackpad: a slightly curved path (bending either way), fast in the
 *  middle and slow at the ends, a small overshoot on longer moves that settles back onto the target. */
async function cursorTo(x, y, ms) {
  const [x0, y0] = await cursorPos();
  const dist = Math.hypot(x - x0, y - y0);
  ms = Math.round(ms * rand(0.85, 1.15));
  const over = dist > 160 ? Math.min(16, dist * 0.035) : 0;
  const ux = dist ? (x - x0) / dist : 0, uy = dist ? (y - y0) / dist : 0;
  await page.evaluate(
    ([x, y, ms, over, ux, uy, bend, skew]) =>
      new Promise((resolve) => {
        const c = document.getElementById("demo-cursor");
        if (!c) return resolve();
        const x0 = Number(c.dataset.x), y0 = Number(c.dataset.y);
        const t0 = performance.now();
        // asymmetric ease: quick start, long soft landing
        const ease = (t) => 1 - Math.pow(1 - Math.pow(t, skew), 3);
        const tx = x + ux * over, ty = y + uy * over;
        const settle = over ? 140 : 0;
        const frame = (now) => {
          const el = now - t0;
          let cx, cy;
          if (el < ms) {
            const e = ease(el / ms);
            const arc = Math.sin(Math.PI * e) * bend;
            cx = x0 + (tx - x0) * e - uy * arc;
            cy = y0 + (ty - y0) * e + ux * arc;
          } else {
            const k = Math.min(1, (el - ms) / Math.max(1, settle));
            const e = 1 - Math.pow(1 - k, 2);
            cx = tx + (x - tx) * e;
            cy = ty + (y - ty) * e;
          }
          c.style.transform = `translate(${cx}px,${cy}px)`;
          if (el < ms + settle) requestAnimationFrame(frame);
          else {
            c.style.transform = `translate(${x}px,${y}px)`;
            c.dataset.x = x;
            c.dataset.y = y;
            sessionStorage.setItem("demo-cursor", JSON.stringify([x, y]));
            resolve();
          }
        };
        requestAnimationFrame(frame);
      }),
    [x, y, ms, over, ux, uy, (Math.random() < 0.5 ? -1 : 1) * Math.min(55, dist * rand(0.05, 0.12)), rand(0.75, 0.95)],
  );
  await page.mouse.move(x, y);
}

async function cursorPos() {
  return page.evaluate(() => {
    const c = document.getElementById("demo-cursor");
    return c ? [Number(c.dataset.x), Number(c.dataset.y)] : [0, 0];
  });
}

/** Moves to an element and clicks (laptop) or taps it (phone), like a person would. */
let waitLimit = 15000;
async function click(loc, { dx = 0, dy = 0, pause = 160, move, timeout = waitLimit } = {}) {
  await loc.waitFor({ state: "visible", timeout });
  await loc.scrollIntoViewIfNeeded();
  const b = await loc.boundingBox();
  const x = Math.round(b.x + b.width / 2 + dx + rand(-0.12, 0.12) * Math.min(b.width, 60)),
    y = Math.round(b.y + b.height / 2 + dy + rand(-0.12, 0.12) * Math.min(b.height, 24));
  if (PHONE) {
    await sleep(pause * rand(0.8, 1.6));
    await page.touchscreen.tap(x, y);
    return;
  }
  const [x0, y0] = await cursorPos();
  const dist = Math.hypot(x - x0, y - y0);
  await cursorTo(x, y, move ?? Math.round(Math.min(620, Math.max(280, dist * 0.55))));
  await sleep(pause * rand(0.8, 1.5));
  await page.evaluate(() => document.getElementById("demo-cursor")?.classList.add("down"));
  await page.mouse.down();
  await sleep(rand(55, 110));
  await page.mouse.up();
  await page.evaluate(() => document.getElementById("demo-cursor")?.classList.remove("down"));
}

/** Rests the cursor on an element for a moment, the way you point at something you're talking about. */
async function hover(loc, ms = 900) {
  await loc.waitFor({ state: "visible", timeout: waitLimit });
  if (PHONE) return sleep(ms);
  const b = await loc.boundingBox();
  const [x0, y0] = await cursorPos();
  const x = Math.round(b.x + b.width * 0.45), y = Math.round(b.y + b.height / 2);
  await cursorTo(x, y, Math.round(Math.min(700, Math.max(320, Math.hypot(x - x0, y - y0) * 0.7))));
  await sleep(ms);
}

/** A hand on a trackpad is never perfectly still: small drifts while you look at the screen. */
async function idle(ms) {
  if (PHONE || ms < 700) return sleep(ms);
  const end = Date.now() + ms;
  while (Date.now() < end - 500) {
    const [x, y] = await cursorPos();
    const nx = Math.max(20, Math.min(VIEW.width - 20, x + Math.round((Math.random() - 0.5) * 70)));
    const ny = Math.max(20, Math.min(VIEW.height - 20, y + Math.round((Math.random() - 0.5) * 40)));
    const step = Math.min(900, end - Date.now() - 300);
    if (step < 300) break;
    await cursorTo(nx, ny, step);
    await sleep(Math.min(400, Math.max(0, end - Date.now() - 200)));
  }
  await sleep(Math.max(0, end - Date.now()));
}

/** Smooth scroll of whatever is under (x, y), eased like a trackpad flick (on a phone it reads as a swipe). */
async function scroll(dy, ms = 1200, at) {
  const [x, y] = at ?? [Math.round(VIEW.width * (PHONE ? 0.5 : 0.6) + rand(-30, 30)), Math.round(VIEW.height * rand(0.5, 0.65))];
  if (!PHONE) {
    const [cx, cy] = await cursorPos();
    if (Math.hypot(cx - x, cy - y) > 200) await cursorTo(x, y, 420);
  }
  await page.mouse.move(x, y);
  // big moves come as a few flicks: e.g. 55 % + 30 % + 15 %, with tiny pauses between
  const parts = Math.abs(dy) > 350 ? (Math.abs(dy) > 900 ? [0.5, 0.32, 0.18] : [0.62, 0.38]) : [1];
  let left = dy;
  for (let p = 0; p < parts.length; p++) {
    const amount = p === parts.length - 1 ? left : Math.round(dy * parts[p]);
    left -= amount;
    const flickMs = (ms / parts.length) * rand(0.8, 1.2);
    // time-based, so a slow wheel event never stretches the flick
    const t0 = Date.now();
    let done = 0;
    while (done !== amount) {
      const t = Math.min(1, (Date.now() - t0) / flickMs);
      const target = Math.round(amount * (1 - Math.pow(1 - t, 2.6))); // ease-out, like a flick
      if (target !== done) await page.mouse.wheel(0, target - done);
      done = target;
      if (t >= 1) break;
      await sleep(12);
    }
    if (p < parts.length - 1) await sleep(rand(90, 220));
  }
}

/** Scrolls until the element sits in the upper third of the screen. */
async function scrollTo(loc, ms = 1600) {
  await loc.waitFor({ state: "attached", timeout: 10000 });
  const b = await loc.boundingBox();
  if (b) await scroll(Math.round(b.y - VIEW.height * 0.28), ms);
}

/** Types like a person (laptop keyboard). */
async function type(text, perChar = 38) {
  for (const ch of text) {
    await page.keyboard.type(ch);
    await sleep(perChar + (/[ ,.]/.test(ch) ? 40 : Math.random() * 25));
  }
}

/** The last breath pause in a recording between `from` and `to` seconds – a clean place for the voice to end. */
function pauseBetween(file, from, to) {
  const r = spawnSync("ffmpeg", ["-v", "info", "-i", file, "-af", "silencedetect=n=-35dB:d=0.18", "-f", "null", "-"], { encoding: "utf8" });
  const starts = [...(r.stderr ?? "").matchAll(/silence_start: ([\d.]+)/g)].map((m) => Number(m[1]));
  return starts.filter((t) => t >= from && t <= to).pop() ?? null;
}

/** Grabs an element and flicks it to the right (a flashcard swipe: "knew it"): a short press, a quick
 *  accelerating throw with a slight lift, released while still moving. */
async function dragRight(loc) {
  await loc.waitFor({ state: "visible", timeout: waitLimit });
  const b = await loc.boundingBox();
  const x0 = Math.round(b.x + b.width * rand(0.42, 0.55)), y0 = Math.round(b.y + b.height * rand(0.5, 0.62));
  if (!PHONE) await cursorTo(x0, y0, 300);
  await page.mouse.move(x0, y0);
  await sleep(rand(70, 120));
  await page.evaluate(() => document.getElementById("demo-cursor")?.classList.add("down"));
  await page.mouse.down();
  const dist = Math.min(VIEW.width * 0.42, 380) * rand(0.9, 1.1), ms = rand(230, 290);
  const t0 = Date.now();
  for (;;) {
    const t = Math.min(1, (Date.now() - t0) / ms);
    const e = Math.pow(t, 1.7); // accelerating, like a throw
    const x = x0 + dist * e, y = y0 - 14 * Math.sin(Math.PI * t * 0.8) + 4 * e;
    await page.mouse.move(x, y);
    if (!PHONE)
      await page.evaluate(([x, y]) => {
        const c = document.getElementById("demo-cursor");
        if (!c) return;
        c.style.transform = `translate(${x}px,${y}px)`;
        c.dataset.x = x;
        c.dataset.y = y;
      }, [x, y]);
    if (t >= 1) break;
    await sleep(10);
  }
  await page.mouse.up();
  await page.evaluate(() => document.getElementById("demo-cursor")?.classList.remove("down"));
}

/** A step that may be missing on some screen size/language: log and go on instead of failing the take. */
async function soft(name, fn) {
  waitLimit = 4000;
  try {
    await fn();
  } catch (e) {
    console.warn(`  (skipped ${name}: ${e.message.split("\n")[0]})`);
  } finally {
    waitLimit = 15000;
  }
}

// ---------------------------------------------------------------- the beats
// A demo is a list of beats in the order the script says them ("upload a PDF, or record the lecture → notes,
// flashcards, tests, quizzes and more"). Each beat shows its feature and nothing else.
const hold = sleep;
let onNote = false; // are we inside a note (vs. the library)?

const back = () => click(iconButton(PHONE ? "arrow_back" : "home"));
const tab = async (icon) => {
  await click(iconButton(icon));
  await hold(250);
};
/** Back to the library, at its top (it otherwise keeps the note's scroll position). */
async function goHome() {
  if (!onNote) return;
  await back();
  await page.waitForURL((u) => !u.pathname.includes("/lectures/"), { timeout: 15000 });
  await page.evaluate(
    () =>
      new Promise((resolve) => {
        const t0 = performance.now();
        const top = () => {
          for (const el of [document.scrollingElement, ...document.querySelectorAll("main, .memo-main, .app-shell-content")])
            if (el) el.scrollTop = 0;
          if (performance.now() - t0 < 400) requestAnimationFrame(top);
          else resolve();
        };
        top();
      }),
  );
  onNote = false;
  await hold(300);
}
/** "New note" from the library: a laptop has big quick-action buttons, a phone opens the sheet first. */
async function create(kind) {
  await goHome();
  if (!PHONE) return click(byText(M[`library.quickAction.${kind}`]));
  await click(byText(M["library.newNote"]));
  await hold(550);
  await click(byText(M[kind === "record" ? "library.create.record" : "library.create.text"]));
}
/** Waiting for a new note (upload, "making cards…") plays fast in the video. */
async function noteOpens() {
  await fast(async () => {
    await page.waitForURL(/\/lectures\//, { timeout: 30000 });
    await vis(page.locator("h1, h2")).waitFor({ timeout: 15000 });
  }, 2);
  onNote = true;
  await hold(500);
  await closeSideChat();
}
/** On a laptop a note opens next to a chat panel; close it so the note gets the whole width. */
async function closeSideChat() {
  if (PHONE) return;
  await soft("close chat", async () => {
    const close = page.locator('button:has(:text-is("close"))').filter({ visible: true });
    if (await close.count()) await click(close.first(), { pause: 120 });
  });
}
async function ensureNote() {
  if (onNote) return;
  await BEATS.open();
}
async function clickPlay() {
  await click(vis(page.locator('button:has(:text-is("play_arrow"))')), { pause: 100 });
}

/** Opens the anatomy note from the library (neuron diagram + action-potential graph, like Klara's videos). */
async function openAnatomy({ title = /^Anatomija|^Anatomy/, keepChat = false } = {}) {
  // "Anatomija – …" in every app language; a link on laptops, a row on phones
  const link = vis(page.getByText(title));
  await link.waitFor({ state: "visible", timeout: 15000 });
  // on shorter screens the note sits under the floating chat bar: scroll it up first
  const b = await link.boundingBox();
  if (b && b.y + b.height > VIEW.height * (PHONE ? 0.62 : 0.8)) {
    await scroll(Math.round(b.y - VIEW.height * 0.35), 550);
    await sleep(150);
  }
  await click(link, { pause: 100 });
  // the note's loading skeleton plays fast, like every other waiting screen
  await fast(async () => {
    await page.waitForURL(/\/lectures\//, { timeout: 15000, waitUntil: "commit" });
    await vis(page.locator(".memo-note-screen h1, .memo-note-screen h2, main h1")).waitFor({ timeout: 15000 });
  }, 4);
  onNote = true;
  await hold(450);
  if (!keepChat) await closeSideChat();
}

const BEATS = {
  /** What Klara shows on memoai.eu (~20 s): the library → the "new note" options (record a lecture, PDF /
   *  PowerPoint) → the anatomy note's neuron diagram and action-potential graph → the tabs (cards, podcast,
   *  quiz…) → the mind map, zoomed in. Pointing and scrolling, nothing filled in. */
  /** The ~20 s tour: library → open a note → scroll it → flashcards (flip one) → quiz (answer one) → mind map →
   *  the AI tutor explaining. */
  async tour() {
    // library, ~1 s
    await idle(PHONE ? 700 : 450);
    // open the first note, close the side chat, scroll down to its graph, ~4.5 s
    await openAnatomy({ title: /^Mikroekonomija|^Microeconomics/ });
    await idle(300);
    await soft("graph", () => scrollTo(page.locator("main img").first(), 1000));
    await idle(PHONE ? 800 : 600);
    await scroll(-4000, 550); // back up to the tabs
    await sleep(rand(150, 300));
    // flashcards: flip one, then drag it away to the right, ~4 s
    await click(iconButton("style"), { pause: 80 });
    await sleep(650);
    await soft("cards", async () => {
      const card = vis(page.locator(".lecture-flashcard"));
      await click(card, { dy: -20, pause: 90 });
      await idle(PHONE ? 800 : 600);
      await dragRight(card);
      await idle(PHONE ? 700 : 450);
    });
    // quiz: answer one, ~2.5 s
    await click(iconButton("quiz"), { pause: 80 });
    await sleep(600);
    await soft("quiz", async () => {
      await click(byText(QUIZ.get(await findQuizPrompt()).correct), { pause: 120 });
      await idle(700);
    });
    // mind map, ~2 s
    await click(iconButton("account_tree"), { pause: 80 });
    await sleep(700);
    await idle(PHONE ? 250 : 350);
    // open a branch: its points fan out
    await soft("open branch", async () => {
      const badge = page.locator("g.memo-mm-badge").nth(1);
      await badge.waitFor({ state: "attached", timeout: 4000 });
      const bb = await badge.boundingBox();
      const x = bb.x + bb.width / 2, y = bb.y + bb.height / 2;
      if (PHONE) {
        await sleep(rand(200, 350));
        await page.touchscreen.tap(x, y);
        await sleep(500);
        // two fingers spread: zoom in toward the opened branch
        await page.mouse.move(x - 40, y);
        await page.keyboard.down("Control");
        for (let i = 0; i < 7; i++) {
          await page.mouse.wheel(0, -7);
          await sleep(40);
        }
        await page.keyboard.up("Control");
        await sleep(900);
      } else {
        await cursorTo(x, y, 450);
        await sleep(rand(120, 200));
        await page.mouse.click(x, y);
        await idle(1000);
      }
    });
    // the voice tutor explains the note out loud, ~5 s
    await soft("voice tutor", async () => {
      await click(iconButton("graphic_eq"), { pause: 80 });
      await sleep(500);
      await click(vis(page.locator(".memo-tutor button").filter({ hasText: M["tutor.start"] ?? "§" }).or(page.locator(".memo-tutor button.memo-tutor-start, .memo-tutor .memo-btn-primary"))), { pause: 100 });
      // "getting ready…" plays fast; the voice starts when it starts speaking
      await fast(() => page.locator(".memo-tutor.phase-speaking").first().waitFor({ timeout: 10000 }), 2.5);
      // let it talk to the end of a sentence (~4 s), then the voice stops there
      const clip = path.join(MEMO, "public/tutor-demo", LANG, "grace-tutor.mp3");
      // (the demo tutor speaks ~5.5 s before it "listens", so the cut is before that)
      const endAt = (fs.existsSync(clip) && pauseBetween(clip, 2, 4.6)) || 4;
      const t0 = Date.now();
      while (Date.now() - t0 < 9000) {
        const at = await page.evaluate(() => {
          const last = [...(window.__demoAudio ?? [])].reverse().find((e) => e.type === "play");
          const el = last && window.__demoEls?.[last.id];
          return el ? el.currentTime : -1;
        });
        if (at >= endAt + 0.1 || (at < 0 && Date.now() - t0 > 6000)) break;
        await sleep(40);
      }
      await page.evaluate(() => {
        const last = [...(window.__demoAudio ?? [])].reverse().find((e) => e.type === "play");
        if (last) window.__demoAudio.push({ type: "stop", id: last.id, t: Date.now() });
      });
    });
  },

  async klara() {
    // 1 · library, ~1 s
    await idle(900);
    // 2 · the ways to make a note, ~4.5 s
    if (PHONE) {
      await click(byText(M["library.newNote"]), { pause: 80 });
      await hold(3800);
      await click(vis(page.locator('button:has(:text-is("close"))')), { pause: 80 });
      await hold(400);
    } else {
      await hover(byText(M["library.quickAction.record"]), 800);
      await hover(byText(M["library.quickAction.document"]), 850);
      await hover(byText(M["library.quickAction.audio"]), 350);
    }
    // 3 · the note's neuron diagram and action-potential graph, ~4 s
    await openAnatomy();
    await soft("diagram", () => scrollTo(page.locator("main img").first(), 800));
    await sleep(900);
    await soft("graph", () => scrollTo(page.locator("main img").nth(1), 700));
    await sleep(1000);
    // 4 · back up to the tabs and point along them, ~3.5 s
    await scroll(-4000, 700);
    await sleep(300);
    if (PHONE) {
      await soft("tab swipe", async () => {
        const bar = vis(page.locator(".memo-tab")).locator("..");
        const bb = await bar.boundingBox();
        await page.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2);
        for (let i = 0; i < 20; i++) {
          await page.mouse.wheel(14, 0);
          await sleep(30);
        }
      });
      await hold(1800);
    } else {
      for (const icon of ["style", "podcasts", "quiz"]) await soft(icon, () => hover(iconButton(icon), 550));
    }
    // 5 · the mind map, zoomed in, ~4.5 s
    await click(iconButton("account_tree"), { pause: 80 });
    await sleep(800);
    if (PHONE) {
      await soft("full screen", () => click(iconButton("open_in_full"), { pause: 80 }));
      await hold(600);
      // spread two fingers: zoom into the map's centre
      await soft("pinch", async () => {
        const map = vis(page.locator("svg:has(g.memo-mm-badge)"));
        const bb = await map.boundingBox();
        await page.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2);
        await page.keyboard.down("Control");
        for (let i = 0; i < 8; i++) {
          await page.mouse.wheel(0, -6);
          await sleep(45);
        }
        await page.keyboard.up("Control");
      });
      await hold(1900);
    } else {
      await soft("zoom", async () => {
        await click(iconButton("add"), { pause: 80 });
        await sleep(450);
        await click(iconButton("add"), { pause: 60 });
      });
      await idle(1100);
    }
  },
  /** Make the notes by recording a lecture: the "new note" options are on screen while the script names them
   *  (PDF / PowerPoint / recording), then the notes and graphs write themselves while the lecture runs. */
  async record(listenMs = 5600) {
    await goHome();
    await idle(700);
    if (PHONE) {
      await click(byText(M["library.newNote"]));
      await hold(1500); // the options: record, upload audio, PDF / document / photo, link
      await click(byText(M["library.create.record"]));
    } else {
      await hover(byText(M["library.quickAction.document"]), 800);
      await click(byText(M["library.quickAction.record"]));
    }
    await idle(listenMs);
    await click(byText(M["creatorDemo.stopAndOpenNotes"]));
    await noteOpens();
  },
  async recordLong() {
    await BEATS.record(8000);
  },
  /** The ~22 s note-taker demo for the hand-written lecture scripts ("open the app, start recording, it makes the
   *  notes, then flashcards, quizzes, tests"): "upload audio" / "record the lecture" → the notes write themselves
   *  while the lecture runs → stop → the finished notes (key points, table) → flip a flashcard → answer a quiz
   *  question → start a practice test. */
  async notetaker() {
    // the ways to make a note, recording picked, ~2.5 s
    await idle(PHONE ? 700 : 500);
    if (PHONE) {
      await click(iconButton("edit_square")); // the phone library's "New" button
      await hold(1300); // the options: record, upload audio, PDF / document / photo, link
      await click(byText(M["library.create.record"]));
    } else {
      await hover(byText(M["library.quickAction.audio"]), 700);
      await click(byText(M["library.quickAction.record"]));
    }
    // the lecture runs, the notes write themselves, ~5 s
    await idle(4200);
    await click(byText(M["creatorDemo.stopAndOpenNotes"]));
    await noteOpens();
    // the finished notes: key points, then the table, ~3 s
    await idle(400);
    await scroll(PHONE ? 560 : 460, 1300);
    await idle(700);
    await scroll(-4000, 550); // back up to the tabs
    await sleep(rand(150, 300));
    // flashcards: flip one, ~2.5 s
    await click(iconButton("style"), { pause: 80 });
    await sleep(600);
    await soft("cards", async () => {
      await click(vis(page.locator(".lecture-flashcard")), { dy: -20, pause: 90 });
      await idle(PHONE ? 900 : 750);
    });
    // quiz: answer one, it turns green, ~2.5 s
    await click(iconButton("quiz"), { pause: 80 });
    await sleep(600);
    await soft("quiz", async () => {
      await click(byText(QUIZ.get(await findQuizPrompt()).correct), { pause: 120 });
      await idle(750);
    });
    // practice test: start it, type a few words of an answer, ~3.5 s
    await click(iconButton("assignment"), { pause: 80 });
    await sleep(600);
    await soft("test", async () => {
      await click(vis(page.getByRole("button", { name: M["study.test.startNew"] })));
      await idle(700);
      await click(vis(page.locator("textarea")));
      await type((await practiceAnswer()).split(" ").slice(0, 4).join(" "), 40);
      await idle(700);
    });
  },
  /** Make the notes from a PDF / PowerPoint / photos: options on screen, pick the document, create. */
  async upload() {
    await goHome();
    await idle(700);
    if (PHONE) {
      await click(byText(M["library.newNote"]));
      await hold(1500);
      await click(byText(M["library.create.text"]));
    } else {
      await hover(byText(M["library.quickAction.record"]), 800);
      await click(byText(M["library.quickAction.document"]));
    }
    await idle(1200); // the picked file
    await click(byText(M["capture.createNote"]));
    await noteOpens();
  },
  /** Open a note that is already in the library. */
  async open() {
    await goHome();
    await idle(700);
    // the anatomy note from the library ("Anatomija – …" in every app language; a link on laptops, a row on phones)
    const link = vis(page.getByText(/^Anatomija|^Anatomy/));
    await link.waitFor({ state: "visible", timeout: 15000 });
    // on shorter screens the note sits under the floating chat bar: scroll it up first
    const b = await link.boundingBox();
    if (b && b.y + b.height > VIEW.height * (PHONE ? 0.62 : 0.8)) {
      await scroll(Math.round(b.y - VIEW.height * 0.35), 900);
      await idle(500);
    }
    await click(link);
    await page.waitForURL(/\/lectures\//, { timeout: 15000, waitUntil: "commit" });
    onNote = true;
    await hold(600);
    await closeSideChat();
    await idle(700);
  },
  /** Read through the notes: two calm scrolls, a pause on what's there. */
  async notes() {
    await ensureNote();
    await idle(700);
    await scroll(PHONE ? 520 : 420, 1700);
    await idle(1300);
  },
  /** The notes with their highlighted key points. */
  async highlights() {
    await ensureNote();
    await idle(900);
    await scroll(PHONE ? 380 : 280, 1500);
    await idle(1800);
    await scroll(PHONE ? 380 : 320, 1500);
    await idle(1600);
  },
  /** Flashcards: question → flip → "knew it" → next card → flip. */
  async cards() {
    await ensureNote();
    await tab("style");
    await idle(900);
    await soft("cards", async () => {
      const card = vis(page.locator(".lecture-flashcard"));
      await click(card, { dy: -20 });
      await idle(1500);
      await click(vis(page.locator(".lecture-flashcard-review-button.easy")));
      await idle(700);
      await click(card, { dy: -20 });
      await idle(1400);
    });
  },
  /** Quiz: two questions answered right (green, then it moves on by itself). */
  async quiz() {
    await ensureNote();
    await tab("quiz");
    await idle(900);
    await soft("quiz", async () => {
      for (let q = 0; q < 2; q++) {
        const { options, correct } = QUIZ.get(await findQuizPrompt());
        await hover(byText(options.find((o) => o !== correct)), 500); // reading the options
        await click(byText(correct));
        await idle(1500);
      }
    });
  },
  /** Quiz with explanations: one right, then one wrong – red, with the right answer and why. */
  async quizWhy() {
    await ensureNote();
    await tab("quiz");
    await idle(900);
    await soft("quiz", async () => {
      let { correct } = QUIZ.get(await findQuizPrompt());
      await click(byText(correct));
      await idle(1500);
      const next = QUIZ.get(await findQuizPrompt());
      await click(byText(next.options.find((o) => o !== next.correct)));
      await idle(2600);
    });
  },
  /** Practice test: an open question, answered in your own words. */
  async test() {
    await ensureNote();
    await tab("assignment");
    await idle(900);
    await soft("test", async () => {
      await click(vis(page.getByRole("button", { name: M["study.test.startNew"] })));
      await idle(1000);
      await click(vis(page.locator("textarea")));
      await type(await practiceAnswer(), 42);
      await idle(900);
    });
  },
  /** Practice test: "Test" → all the questions, one after another. */
  async testQuestions() {
    await ensureNote();
    await idle(500);
    await hover(iconButton("assignment"), 700);
    await tab("assignment");
    await idle(1000);
    await soft("test", async () => {
      await click(vis(page.getByRole("button", { name: M["study.test.startNew"] })));
      for (let i = 0; i < 3; i++) {
        await idle(1500);
        await click(vis(page.getByRole("button", { name: M["common.next"], exact: true })));
      }
      await idle(1500);
    });
  },
  /** Practice test with a grade: answer every question, hand it in, get the result. */
  async testGraded() {
    await ensureNote();
    await tab("assignment");
    await idle(800);
    await soft("graded test", async () => {
      await click(vis(page.getByRole("button", { name: M["study.test.startNew"] })));
      await idle(700);
      for (let i = 0; i < 8; i++) {
        await click(vis(page.locator("textarea")), { pause: 60 });
        await fast(async () => type(await practiceAnswer(), 30), 3);
        const submit = page.getByRole("button", { name: M["test.submit"], exact: true }).filter({ visible: true });
        if (await submit.count()) {
          await click(submit.first());
          break;
        }
        await click(vis(page.getByRole("button", { name: M["common.next"], exact: true })));
        await hold(300);
      }
      await fast(() => sleep(3500), 2); // "grading…"
      await idle(2600);
    });
  },
  /** Mind map: the whole note as a map, zoomed in a little. */
  async mindmap() {
    await ensureNote();
    await tab("account_tree");
    await idle(1500);
    if (!PHONE) await soft("zoom", () => click(iconButton("add")));
    await idle(1300);
  },
  /** Mind map: open a topic and see everything under it. */
  async mindmapOpen() {
    await BEATS.mindmap();
    await soft("open topic", async () => {
      await click(page.locator("g.memo-mm-badge").filter({ visible: true }).nth(1));
      await idle(1800);
    });
  },
  async podcast() {
    await ensureNote();
    await tab("podcasts");
    await idle(800);
    await soft("podcast play", clickPlay);
    await idle(2600);
  },
  /** The app reads the notes out loud (word by word highlighted). */
  async readAloud() {
    await ensureNote();
    await tab("description");
    await idle(600);
    await soft("read aloud", async () => {
      await click(iconButton("headphones"));
      await idle(3200);
    });
  },
  /** AI tutor: ask the note, get an explanation, close the chat again. */
  async tutor() {
    await ensureNote();
    await soft("tutor", async () => {
      if (PHONE) {
        await tab("description"); // the phone's chat bar sits under the notes tab
        await idle(400);
        await click(vis(page.locator(".memo-m-chatbar")));
      } else await click(vis(page.locator('button:has(:text-is("forum"))')));
      await idle(900);
      await click(byText(M["chat.suggestion.explain"]));
      await idle(3000);
      await click(vis(page.locator('button:has(:text-is("close"))')));
      await idle(500);
    });
  },
};

const BEAT_LIST = (arg("beats", "") || "").split(",").filter(Boolean);
for (const b of BEAT_LIST) if (!BEATS[b]) throw new Error(`unknown beat "${b}" (${Object.keys(BEATS).join(", ")})`);

async function scenes() {
  if (!BEAT_LIST.length) throw new Error("--beats a,b,c is required");
  await hold(300);
  for (const b of BEAT_LIST) {
    await BEATS[b]();
    await snap(b);
  }
  await idle(400);
}

// What the test answer reads like in each language (written by a student, not the app).
const TEST_ANSWER = {
  sl: "Signal gre po dendritu v telo nevrona, potem po aksonu do sinapse.",
  hr: "Signal ide dendritom u tijelo neurona, zatim aksonom do sinapse.",
  bs: "Signal ide dendritom u tijelo neurona, zatim aksonom do sinapse.",
  sr: "Signal ide dendritom u telo neurona, zatim aksonom do sinapse.",
  en: "The signal goes through the dendrite into the cell body, then down the axon to the synapse.",
};

async function practiceAnswer() {
  for (const [prompt, answer] of PRACTICE) {
    if (await page.getByText(prompt, { exact: true }).filter({ visible: true }).count()) return answer;
  }
  return TEST_ANSWER[LANG] ?? TEST_ANSWER.sl;
}

async function findQuizPrompt() {
  for (const prompt of QUIZ.keys()) {
    if (await page.getByText(prompt, { exact: true }).filter({ visible: true }).count()) return prompt;
  }
  return null;
}

// ---------------------------------------------------------------- capture
async function run({ capture }) {
  // A real device scale factor (not Playwright's emulated one): the screencast then sends full-resolution frames.
  const browser = await chromium.launch({
    args: [
      "--force-color-profile=srgb",
      "--hide-scrollbars",
      `--force-device-scale-factor=${SCREEN.dsf}`,
      `--window-size=${VIEW.width},${VIEW.height}`,
    ],
  });
  const ctx = await browser.newContext({
    viewport: null,
    hasTouch: PHONE,
    colorScheme: "light",
    locale: LANG,
    userAgent: ANDROID
      ? "Mozilla/5.0 (Linux; Android 15; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36"
      : PHONE
        ? "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
        : undefined,
  });
  await ctx.addCookies([{ name: "memo-locale", value: LANG, url: APP }]);
  await ctx.addInitScript(() => localStorage.setItem("nota-theme", "light"));
  await ctx.addInitScript(initScript, { cursorSvg: CURSOR_SVG, laptop: !PHONE });
  page = await ctx.newPage();
  await page.goto(`${APP}/creator/college`, { waitUntil: "networkidle" });
  await sleep(2500); // fonts, hydration, entrance fade
  onNote = false;

  const frames = [];
  let cdp;
  if (capture) {
    fs.rmSync(FRAMES, { recursive: true, force: true });
    fs.mkdirSync(FRAMES, { recursive: true });
    cdp = await ctx.newCDPSession(page);
    cdp.on("Page.screencastFrame", async ({ data, metadata, sessionId }) => {
      const file = path.join(FRAMES, `${String(frames.length).padStart(6, "0")}.jpg`);
      frames.push({ t: metadata.timestamp, file });
      fs.writeFile(file, Buffer.from(data, "base64"), () => {});
      try {
        await cdp.send("Page.screencastFrameAck", { sessionId });
      } catch {}
    });
    await cdp.send("Page.startScreencast", {
      format: "jpeg",
      quality: 88,
      everyNthFrame: 1,
      maxWidth: VIEW.width * SCREEN.dsf,
      maxHeight: VIEW.height * SCREEN.dsf,
    });
  }
  const t0 = Date.now();
  if (capture) chapterClock = t0;
  await scenes();
  await hold(500);
  const seconds = (Date.now() - t0) / 1000;
  const audioLog = capture ? await page.evaluate(() => window.__demoAudio ?? []).catch(() => []) : [];
  if (capture) await cdp.send("Page.stopScreencast");
  await sleep(500);
  await browser.close();
  return { frames, seconds, audioLog };
}

function browserBars() {
  // Fake browser chrome around the page so the video reads as someone on memoai.eu.
  const file = path.join(HERE, "frames", `bars-${DEVICE}.png`);
  return file;
}

async function drawBars() {
  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: SCREEN.w, height: SCREEN.h }, deviceScaleFactor: SCREEN.dsf });
  await p.setContent({ mac: macBarsHtml, windows: windowsBarsHtml, phone: phoneBarsHtml, android: androidBarsHtml }[DEVICE]());
  await p.screenshot({ path: browserBars(), omitBackground: true });
  await browser.close();
}

const FONT = `-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',Helvetica,Arial,sans-serif`;
function macBarsHtml() {
  return `<html><body style="margin:0;background:transparent;font-family:${FONT}">
  <div style="height:${SCREEN.top}px;background:#f6f6f7;border-bottom:1px solid #dcdce0;display:flex;align-items:center;padding:0 16px;gap:18px;box-sizing:border-box">
    <div style="display:flex;gap:8px">${["#ff5f57", "#febc2e", "#28c840"].map((c) => `<span style="width:11px;height:11px;border-radius:50%;background:${c};display:block"></span>`).join("")}</div>
    <div style="display:flex;gap:14px;color:#8a8a8e;font-size:18px;margin-left:10px">&#x2039;&nbsp;&nbsp;&#x203A;</div>
    <div style="flex:1;display:flex;justify-content:center">
      <div style="width:440px;height:28px;border-radius:8px;background:#e9e9ec;display:flex;align-items:center;justify-content:center;gap:7px;color:#1d1d1f;font-size:13px">
        <svg width="11" height="13" viewBox="0 0 11 13"><rect x="1" y="5.5" width="9" height="7" rx="1.6" fill="#6e6e73"/><path d="M3 5.6V4a2.5 2.5 0 0 1 5 0v1.6" stroke="#6e6e73" stroke-width="1.5" fill="none"/></svg>
        memoai.eu</div></div>
    <div style="width:96px;display:flex;justify-content:flex-end;gap:16px;color:#8a8a8e;font-size:17px">&#x2B06;&#xFE0E;&nbsp;&#xFF0B;</div>
  </div></body></html>`;
}
const FAVICON = () =>
  `data:image/png;base64,${fs.readFileSync(path.join(MEMO, "public/memo-favicon-96x96.png")).toString("base64")}`;
function windowsBarsHtml() {
  const icon = (d, size = 16) =>
    `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="#474747" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  return `<html><body style="margin:0;background:transparent;font-family:'Segoe UI Variable','Segoe UI',${FONT}">
  <div style="height:${SCREEN.top}px;display:flex;flex-direction:column">
    <div style="height:40px;background:#dfe3e8;display:flex;align-items:flex-end;padding-left:8px">
      <div style="width:240px;height:34px;background:#fff;border-radius:9px 9px 0 0;display:flex;align-items:center;gap:9px;padding:0 10px;box-sizing:border-box;font-size:12px;color:#1f1f1f">
        <img src="${FAVICON()}" style="width:16px;height:16px"><span style="flex:1">Memo AI</span><span style="color:#5f6368;font-size:13px">&#x2715;</span></div>
      <div style="width:34px;height:34px;display:flex;align-items:center;justify-content:center;color:#474747;font-size:18px">+</div>
      <div style="flex:1"></div>
      ${["&#x2014;", "&#x25A2;", "&#x2715;"].map((g) => `<div style="width:46px;height:40px;display:flex;align-items:center;justify-content:center;color:#1f1f1f;font-size:13px;align-self:flex-start">${g}</div>`).join("")}
    </div>
    <div style="height:40px;background:#fff;border-bottom:1px solid #e3e3e3;display:flex;align-items:center;gap:16px;padding:0 14px;box-sizing:border-box">
      ${icon('<path d="M19 12H5M12 19l-7-7 7-7"/>')}${icon('<path d="M5 12h14M12 5l7 7-7 7"/>', 16).replace('stroke="#474747"', 'stroke="#b4b4b4"')}${icon('<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>')}
      <div style="flex:1;height:30px;border-radius:15px;background:#eef1f5;display:flex;align-items:center;gap:10px;padding:0 14px;font-size:14px;color:#1f1f1f">
        ${icon('<path d="M4 7h10M4 17h16M18 7h2M8 17"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/>', 14)}memoai.eu</div>
      ${icon('<path d="M12 3l2.7 5.6 6.2.9-4.5 4.4 1 6.1L12 17.1 6.6 20l1-6.1L3.1 9.5l6.2-.9z"/>')}
      <div style="width:24px;height:24px;border-radius:50%;background:#c9b8f5"></div>
      <div style="color:#474747;font-size:18px;line-height:1">&#x22EE;</div>
    </div>
  </div></body></html>`;
}
function androidBarsHtml() {
  const ROBOTO = `'Roboto','Google Sans',${FONT}`;
  const i = (d, w = 16, h = 16, vb = "0 0 24 24") => `<svg width="${w}" height="${h}" viewBox="${vb}">${d}</svg>`;
  return `<html><body style="margin:0;background:transparent;font-family:${ROBOTO}">
  <div style="position:absolute;top:0;left:0;right:0;height:${SCREEN.top}px;background:#fff">
    <div style="height:28px;display:flex;align-items:center;justify-content:space-between;padding:0 16px 0 18px;font-size:13.5px;color:#1f1f1f;font-weight:500">
      <span>12:41</span>
      <span style="display:flex;align-items:center;gap:5px">
        ${i('<path d="M12 18.5 9.2 15.6a4 4 0 0 1 5.6 0zM5.6 12a9.1 9.1 0 0 1 12.8 0l-1.8 1.8a6.6 6.6 0 0 0-9.2 0zM2 8.4a14.2 14.2 0 0 1 20 0l-1.8 1.8a11.6 11.6 0 0 0-16.4 0z" fill="#1f1f1f"/>', 15, 15)}
        ${i('<path d="M2 21h3v-5H2zm5 0h3V12H7zm5 0h3V8h-3zm5 0h3V3h-3z" fill="#1f1f1f"/>', 14, 14)}
        <span style="display:flex;align-items:center;gap:2px">${i('<rect x="1" y="5" width="18" height="11" rx="2.5" fill="none" stroke="#1f1f1f" stroke-width="1.6"/><rect x="3" y="7" width="12" height="7" rx="1.2" fill="#1f1f1f"/><rect x="20" y="8.5" width="2" height="4" rx=".8" fill="#1f1f1f"/>', 20, 14, "0 0 23 20")}<span style="font-size:12px">78%</span></span>
      </span>
    </div>
    <div style="height:56px;display:flex;align-items:center;gap:12px;padding:0 10px 0 12px;box-sizing:border-box">
      ${i('<path d="M3 11.5 12 4l9 7.5M5.5 10v9.5h13V10" fill="none" stroke="#444746" stroke-width="2" stroke-linejoin="round"/>', 22, 22)}
      <div style="flex:1;height:44px;border-radius:22px;background:#eef1f6;display:flex;align-items:center;gap:10px;padding:0 14px;font-size:16px;color:#1f1f1f">
        ${i('<path d="M4 7h10M18 7h2M4 17h4M12 17h8" stroke="#444746" stroke-width="2" stroke-linecap="round"/><circle cx="16" cy="7" r="2.2" fill="none" stroke="#444746" stroke-width="2"/><circle cx="10" cy="17" r="2.2" fill="none" stroke="#444746" stroke-width="2"/>', 18, 18)}memoai.eu</div>
      <div style="width:20px;height:20px;border:2px solid #444746;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#444746;box-sizing:border-box">1</div>
      <div style="color:#444746;font-size:20px;line-height:1">&#x22EE;</div>
    </div>
  </div>
  <div style="position:absolute;bottom:0;left:0;right:0;height:${SCREEN.bottom}px;background:#fff;display:flex;align-items:center;justify-content:center">
    <div style="width:108px;height:4px;border-radius:2px;background:#1f1f1f;opacity:.85"></div>
  </div></body></html>`;
}
function phoneBarsHtml() {
  const time = "9:41";
  return `<html><body style="margin:0;background:transparent;font-family:${FONT}">
  <div style="position:absolute;top:0;left:0;right:0;height:${SCREEN.top}px;background:#fff;display:flex;align-items:flex-end;justify-content:space-between;padding:0 30px 10px 44px;box-sizing:border-box">
    <span style="font-weight:600;font-size:17px;color:#000">${time}</span>
    <span style="display:flex;gap:6px;align-items:center">
      <svg width="18" height="12" viewBox="0 0 18 12">${[0, 1, 2, 3].map((i) => `<rect x="${i * 4.8}" y="${9 - i * 3}" width="3.2" height="${3 + i * 3}" rx="1" fill="#000"/>`).join("")}</svg>
      <svg width="16" height="12" viewBox="0 0 16 12"><path d="M8 11.5 5.6 9a3.4 3.4 0 0 1 4.8 0zM3.4 6.8a6.5 6.5 0 0 1 9.2 0l-1.4 1.4a4.5 4.5 0 0 0-6.4 0zM1.1 4.5a9.8 9.8 0 0 1 13.8 0l-1.4 1.4a7.8 7.8 0 0 0-11 0z" fill="#000"/></svg>
      <svg width="27" height="13" viewBox="0 0 27 13"><rect x=".5" y=".5" width="23" height="12" rx="3.6" fill="none" stroke="#000" opacity=".4"/><rect x="2" y="2" width="17" height="9" rx="2.2" fill="#000"/><path d="M25 4.5v4a2 2 0 0 0 0-4" fill="#000" opacity=".5"/></svg>
    </span>
  </div>
  <div style="position:absolute;bottom:0;left:0;right:0;height:${SCREEN.bottom}px;background:rgba(255,255,255,.96);border-top:1px solid #e3e3e6;display:flex;justify-content:center;padding-top:9px;box-sizing:border-box">
    <div style="width:350px;height:40px;border-radius:20px;background:#ececef;display:flex;align-items:center;justify-content:space-between;padding:0 14px;box-sizing:border-box;color:#1d1d1f;font-size:16px">
      <span style="font-size:15px;color:#3a3a3c">aA</span>
      <span style="display:flex;align-items:center;gap:6px"><svg width="10" height="12" viewBox="0 0 11 13"><rect x="1" y="5.5" width="9" height="7" rx="1.6" fill="#6e6e73"/><path d="M3 5.6V4a2.5 2.5 0 0 1 5 0v1.6" stroke="#6e6e73" stroke-width="1.5" fill="none"/></svg>memoai.eu</span>
      <span style="font-size:16px;color:#3a3a3c">&#x21BB;</span>
    </div>
  </div></body></html>`;
}

/** The page's sounds as segments on the video's timeline: [{file, at, from, dur}] (seconds). */
async function audioTrack(log, seconds) {
  const base = chapterClock;
  const segs = [];
  for (const [i, e] of log.entries()) {
    if (e.type !== "play" || e.muted || !e.src) continue;
    const stop = log.slice(i + 1).find((x) => x.id === e.id && x.type === "stop");
    const a = (e.t - base) / 1000, b = Math.min(seconds, ((stop?.t ?? base + seconds * 1000) - base) / 1000);
    if (b <= a) continue;
    const file = path.join(FRAMES, `audio-${segs.length}${path.extname(new URL(e.src).pathname) || ".mp3"}`);
    const res = await fetch(new URL(e.src, APP));
    if (!res.ok) continue;
    fs.writeFileSync(file, Buffer.from(await res.arrayBuffer()));
    segs.push({ file, at: videoTime(a), from: e.offset ?? 0, dur: videoTime(b) - videoTime(a), volume: e.volume ?? 1 });
  }
  if (segs.length) console.log(`  audio: ${segs.map((x) => `${path.basename(x.file)} @${x.at.toFixed(1)}s ${x.dur.toFixed(1)}s`).join(", ")}`);
  return segs;
}

function encode(frames, seconds, audio = []) {
  fs.mkdirSync(OUT, { recursive: true });
  // Screencast timestamps are wall-clock seconds; chapterClock started at the same moment as the scenes.
  const base = chapterClock / 1000;
  const vt = (t) => videoTime(t - base);
  const end = base + seconds + 0.2;
  const lines = ["ffconcat version 1.0"];
  frames.forEach((f, i) => {
    const next = i + 1 < frames.length ? frames[i + 1].t : end;
    lines.push(`file '${f.file}'`, `duration ${Math.max(0.001, vt(next) - vt(f.t)).toFixed(4)}`);
  });
  lines.push(`file '${frames.at(-1).file}'`);
  const list = path.join(FRAMES, "list.txt");
  fs.writeFileSync(list, lines.join("\n"));
  const outFile = path.join(OUT, `memo-ai-demo-${NAME}-${DEVICE}-${LANG}.mp4`);
  const W = SCREEN.w * SCREEN.dsf, H = SCREEN.h * SCREEN.dsf;
  const filter =
    `[0:v]format=rgb24,scale=${W}:${VIEW.height * SCREEN.dsf}:flags=lanczos,format=rgb24,pad=${W}:${H}:0:${SCREEN.top * SCREEN.dsf}:white,fps=60[page];` +
    `[page][1:v]overlay=0:0,scale=${SCREEN.outW}:-2:flags=lanczos,format=yuv420p[v]`;
  // the page's sounds, each placed where it played and cut where it stopped
  const audioIn = audio.flatMap((a) => ["-i", a.file]);
  let audioFilter = "", audioMap = [];
  if (audio.length) {
    audioFilter =
      ";" +
      audio
        .map((a, k) =>
          `[${k + 2}:a]atrim=start=${a.from.toFixed(3)}:duration=${a.dur.toFixed(3)},asetpts=PTS-STARTPTS,` +
          `afade=t=out:st=${Math.max(0, a.dur - 0.12).toFixed(3)}:d=0.12,volume=${a.volume.toFixed(2)},` +
          `adelay=${Math.round(a.at * 1000)}:all=1[a${k}]`,
        )
        .join(";") +
      ";" + audio.map((_, k) => `[a${k}]`).join("") + `amix=inputs=${audio.length}:normalize=0,apad[aout]`;
    audioMap = ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"];
  }
  execFileSync("ffmpeg", [
    "-v", "error", "-y",
    "-f", "concat", "-safe", "0", "-i", list,
    "-loop", "1", "-i", browserBars(),
    ...audioIn,
    "-filter_complex", filter + audioFilter, "-map", "[v]", ...audioMap,
    "-t", String(videoTime(seconds)),
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-movflags", "+faststart",
    outFile,
  ], { stdio: "inherit" });
  return outFile;
}

if (!process.argv.includes("--no-warm")) {
  console.log("warm-up run (compiles every screen once)…");
  await run({ capture: false });
}
console.log(`recording ${DEVICE} ${LANG}…`);
const { frames, seconds, audioLog } = await run({ capture: true });
console.log(`${frames.length} frames in ${seconds.toFixed(1)} s (${(frames.length / seconds).toFixed(1)} fps)`);
await drawBars();
const video = encode(frames, seconds, await audioTrack(audioLog, seconds));
console.log(`wrote ${video} (${videoTime(seconds).toFixed(1)} s)`);
