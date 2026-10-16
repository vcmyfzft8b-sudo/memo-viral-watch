# Memo AI demo recordings

The app demo creators play while filming: a creator opens it on their laptop or phone, plays it from start to end
while they talk about Memo AI, and films the screen (finger pointing), the way Klara (@school.hacks.byklara) does
in her Memo AI videos. One demo for every format.


It is ~20 s (phone ~19 s, laptops ~24 s) and moves like a person: curved, uneven cursor paths with a small
overshoot, trackpad/thumb flicks when scrolling, varied pauses.

1. the library (~1 s)
2. open a note and scroll down to its graph (~4 s)
3. flashcards: flip one, then drag it away to the right ("knew it") (~4 s)
4. quiz: answer one, it turns green (~2.5 s)
5. the mind map (~2 s)
6. the voice tutor ("Inštruktor" / "Objašnjenje"): start → it talks through the note (~5 s)

It is a screen recording of the app's offline demo (`/creator/college`): the real app UI with fixed demo notes,
no account, no AI. The live demo hides the voice tutor tab (it needs a microphone and the AI), so the recordings
use a local Memo AI copy (`~/dev/Memo_AI-demo-tutor`, branch `demo/voice-tutor-in-creator-demo`) whose creator
demo shows that tab, played by the same scripted walkthrough the landing page uses (`LandingTutorDemo`).

## Where they are

`out/final/Balkan/` (Croatian, ijekavian app) and `out/final/Slovenija/` (Slovenian app):

| file | looks like | size |
|---|---|---|
| `Memo AI demo – Mac (…).mp4` | MacBook, Safari bar with memoai.eu, Mac cursor | 1920×1200 |
| `Memo AI demo – Windows (…).mp4` | Windows laptop, Chrome window with memoai.eu, Windows cursor | 1920×1080 |
| `Memo AI demo – telefon (…).mp4` | iPhone, status bar + Safari address bar memoai.eu | 1080×2342 |

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
