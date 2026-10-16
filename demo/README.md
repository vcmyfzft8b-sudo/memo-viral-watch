# Memo AI demo recordings

The app demo creators play while filming: a creator opens it on their laptop or phone, plays it from start to end
while they talk about Memo AI, and films the screen (finger pointing), the way Klara (@school.hacks.byklara) does
in her Memo AI videos. One demo for every format.

It shows what Klara shows on memoai.eu, in her timing (her screen part is ~20 s; the demo is ~24–27 s with a
second to start and stop):

1. the library (~1 s)
2. the ways to make a note – record a lecture, PDF / PowerPoint, audio (~5 s)
3. the anatomy note: the neuron diagram, then the action-potential graph (~4 s)
4. back up to the tabs: flashcards, podcast, quiz … (~4 s)
5. the mind map, zoomed in (~5 s)

Pointing and scrolling only – nothing is filled in, like in her videos. It is a screen recording of the app's
offline demo (`/creator/college` in the Memo AI repo): the real app UI with fixed demo notes, no account, no AI.

## Where they are

`out/final/Balkan/` (Croatian, ijekavian app) and `out/final/Slovenija/` (Slovenian app):

| file | looks like | size |
|---|---|---|
| `Memo AI demo – Mac (…).mp4` | MacBook, Safari bar with memoai.eu, Mac cursor | 1920×1200 |
| `Memo AI demo – Windows (…).mp4` | Windows laptop, Chrome window with memoai.eu, Windows cursor | 1920×1080 |
| `Memo AI demo – telefon (…).mp4` | iPhone, status bar + Safari address bar memoai.eu | 1080×2342 |

## Make them again

Needs the Memo AI repo at `~/dev/Memo_AI` running locally (`next dev` on port 3555), Node 22+ and ffmpeg.

```bash
cd demo && npm install && npx playwright install chromium
node make_all.mjs            # all 6 (skips ones already in out/demos; --redo records them again)
node make_all.mjs phone      # only the phone versions
node record.mjs --device mac --lang hr --beats klara --name test --debug   # one take, screenshots in out/
```

The walkthrough is the `klara` beat in `record.mjs` (other beats there – record, upload, cards, quiz, test,
podcast, read aloud, tutor … – can be combined with `--beats a,b,c` for other demos). After a fresh `next dev`
start, run one take without `--no-warm` first so every screen is compiled.
