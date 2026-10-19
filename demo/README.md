# Memo AI demo recordings

The app demo creators play while filming: a creator opens it on their laptop or phone, plays it from start to end
while they talk about Memo AI, and films the screen (finger pointing), the way Klara (@school.hacks.byklara) does
in her Memo AI videos. One demo for every format.


It is ~20 s (phones ~20 s, laptops ~25 s), with sound, and moves like a person: a real-size cursor on curved, uneven paths
with a small overshoot, trackpad/thumb flicks when scrolling, varied pauses, the card flicked away in ~0.25 s.

1. the library (~1 s)
2. open a note and scroll down to its graph (~4 s)
3. flashcards: flip one, then flick it away to the right ("knew it") (~3.5 s)
4. quiz: answer one, it turns green (~2.5 s)
5. the mind map: a branch is opened and its points fan out (on phones a pinch-zoom toward it) (~3 s)
6. the voice tutor ("Inštruktor" / "Objašnjenje"): start → it talks through the note, out loud (~5 s)

The sound is the tutor's own recorded voice: the recorder logs every clip the page plays (when it starts and
stops) and mixes the same file into the video at that moment. The voice ends on the clip's breath pause around
4 s, so it never stops mid-word.

It is a screen recording of the app's offline demo (`/creator/college`): the real app UI with fixed demo notes,
no account, no AI. The live demo hides the voice tutor tab (it needs a microphone and the AI), so the recordings
use a local Memo AI copy (`~/dev/Memo_AI-demo-tutor`, branch `demo/voice-tutor-in-creator-demo`) whose creator
demo shows that tab, played by the same scripted walkthrough the landing page uses (`LandingTutorDemo`).

## Where they are

`out/final/Balkan/` (Croatian, ijekavian app) and `out/final/Slovenija/` (Slovenian app):

| file | looks like | size |
|---|---|---|
| `Memo AI demo – Mac (…).mp4` | MacBook Pro 16", Safari bar with memoai.eu, macOS cursor | 1920×1240 |
| `Memo AI demo – Windows (…).mp4` | 1080p laptop at 100 %, Chrome window with memoai.eu, Windows cursor | 1920×1080 |
| `Memo AI demo – iPhone (…).mp4` | iPhone, iOS status bar + Safari address bar memoai.eu | 1080×2342 |
| `Memo AI demo – Android (…).mp4` | Samsung Galaxy, Android status bar, Chrome address bar memoai.eu, gesture bar | 1080×2340 |

On the laptops the flashcard may use the free height under it (the app caps it at 22rem; the recordings allow
27rem), so it reads as big as on a large desktop window.

## The note-taker demo (hand-written lecture scripts)

`node make_all.mjs --demo notetaker` (~28 s, phones ~23 s), what creators really see in the app: the "new note"
options → the production record screen (mic orb, 00:00 → start, the clock runs, the live wave moves) → the sheet is
closed (no note is made from a few seconds of recording - that looks fake, user 19 Oct 2026) → an existing note from
the library (key points, table) → flip a flashcard → answer a quiz question → the practice test → a quick look at the
other features (speed reading, memory palace, mind map, podcast).

The creator demo stages a file in the record sheet (no record screen) and `/creator/college` swaps the sheet for its
scripted "listening" takeover, so these recordings use `/creator` of a local Memo AI copy whose record sheet is not
staged: `~/dev/Memo_AI-demo-record` (git worktree of ~/dev/Memo_AI, branch `demo/production-record-sheet`, one change
in `note-source-modal.tsx`; node_modules cloned with `cp -Rc`, Turbopack refuses a symlink). The browser gets a fake
microphone, so the screen records for real.

```bash
cd ~/dev/Memo_AI-demo-record && npx next dev -p 3558        # Node 24 (/opt/homebrew/opt/node@24/bin)
cd demo && DEMO_APP=http://localhost:3558 DEMO_MEMO=~/dev/Memo_AI-demo-record node make_all.mjs --demo notetaker --redo
```

Files: `out/final/<Balkan|Slovenija>/Memo AI demo zapiski – <device> (…).mp4`; on Drive in `Memo AI demo
posnetki/Slovenija/Zapiski` and `…/Balkan/Bilješke` (config `demo_videos_notetaker`; `rclone copyto` onto the same
names keeps the links).

## Make them again

Needs that Memo AI copy running locally (`next dev` on port 3556, `.claude/launch.json` → memo-app-demo-tutor),
Node 22+ and ffmpeg.

```bash
cd demo && npm install && npx playwright install chromium
node make_all.mjs            # all 6 (skips ones already in out/demos; --redo records them again)
node make_all.mjs phone      # only the phone versions
node record.mjs --device mac --lang hr --beats tour --name test --app http://localhost:3556 \
  --memo ~/dev/Memo_AI-demo-tutor --debug                                  # one take, screenshots in out/
```

The walkthrough is the `tour` beat in `record.mjs` (`klara` is Klara's own walkthrough – options, diagrams, tabs,
mind map; other beats – record, upload, cards, quiz, test, podcast, read aloud, tutor … – can be combined with
`--beats a,b,c` for other demos). After a fresh `next dev`
start, run one take without `--no-warm` first so every screen is compiled.
