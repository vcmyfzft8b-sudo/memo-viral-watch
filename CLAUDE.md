# Memo AI viral watch – notes for Claude

Separate copy of the JobStep viral watcher (~/dev/jobstep-viral-watch) – never mix the two (repo, Notion, Discord,
secrets, state are all separate). Read README.md first.

What it does: watches Astra AI creators in Serbia, Croatia, Bosnia and Herzegovina, Montenegro (Lightreel + TikTok +
Claude, every 3 days) and turns their viral formats into Memo AI creator pages in two markets:
`sh` (Serbo-Croatian, Latin script, ijekavian) and `sl` (Slovenian). Every 6 hours on GitHub Actions; state on the
`state` branch.

## Rules
- Explain things to the user in very simple, short sentences.
- Secrets: never write keys into the repo or GitHub yourself. The user saves them with `scripts/save_*.sh`
  (`scripts/connect_all.sh` walks through all). The browser pane's copy buttons do not reach the Mac clipboard – the
  user copies in their own browser / Discord app. Claude runs only on the user's subscription (CLAUDE_CODE_OAUTH_TOKEN).
- Never delete pages/data the user did not name; Notion trash only with OK.
- Alerts go to Discord `#astra-alerts` (DISCORD_ALERTS_WEBHOOK_URL), not Slack.
- Approved scripts (registry/approved_scripts.json) are locked – only change with the user's OK.

## Script rules (user's decision, 10 Oct 2026)
- A script is the ORIGINAL video transcribed and translated (if needed) almost one to one – same sentences, order,
  words, jokes, numbers, claims. Only these change: the app (Astra AI, Studyflash, …) -> Memo AI at the same spots,
  its website -> memoai.eu, an app feature Memo AI lacks -> the closest real one, the page language's spelling
  (ijekavian / Slovenian). No "independent wording", no toning down.
- Tone: 🇸🇮 Slovenian scripts (translations) are casual spoken Slovenian the way teenagers talk on TikTok
  (markets.TEXT["sl"]["style"]) and always say "AI", never "umetna inteligenca"; 🇧🇦🇭🇷🇷🇸🇲🇪 Balkan scripts are
  transcripts and stay as spoken.
- Localization: 🇸🇮 Slovenian scripts turn country-specific things (faculties, schools, exams, cities, shops, prices,
  discounts) into REAL Slovenian ones with correct names (markets.TEXT['sl']['localize']); 🇧🇦🇭🇷🇷🇸🇲🇪 Balkan
  scripts keep the original's names and the note under the video says creators may swap them for their own
  country's (TEXT['sh']['local_note']).
- No stage directions (user's decision, 11 Oct 2026): a script holds only what is said (or the on-screen texts of a
  silent video). The only brackets are the app link cue "(Memo AI · memoai.eu/…)" and 📎 material cues. Filming, acting
  and editing come from the example video (the note says: copy it as closely as possible) and the visual hook
  section (`brand.NO_DIRECTIONS` is in every writer/checker prompt; `mode=strip-directions` cleans pages; `verify`
  flags leftovers). Dialogue formats label speakers ("Memo AI:" / "Ti:").
- Visual hook section = ONE sentence (two at most): "Napravi isti vizuelni hook kao u videu za inspiraciju: …" (what
  the example does in its first seconds) + one line "Želiš drugi vizuelni hook? Izaberi jedan iz Visual Hook Lab."
  Nothing else (`reword.fix_directions` enforces it, `verify` checks it).

## Where things are
- Who is who + real Memo AI features: `watcher/brand.py` (checked against the Memo AI app code). Market texts and
  language rules: `watcher/markets.py`.
- Notion (separate workspace, free plan → uploads ≤ 5 MiB, `watcher/media.py` compresses): root "Memo AI – TikTok
  formati", one guide page per market (list "👉 … (OBAVEZNO/OBVEZNO)" laid out 1:1 like the Parakeet list, all formats,
  archive, Visual Hook Lab = copy of Parakeet's, translated). Page ids: `state/notion.json`.
- App links on pages → https://memoai.eu/creator (user's choice); creators SAY memoai.eu.
- No shares/saves bar (user's choice, 10 Oct 2026): only views (100k+) decide what becomes a format.
- Brand matching knows declined forms (Astri, Astru, Astro …): `brand.SOURCE_RE`.
- Own Memo AI creators: off until there is a Memo AI campaign in Megasheet (`config.json` → "megasheet").

## Run things
`gh workflow run watch.yml -R vcmyfzft8b-sudo/memo-viral-watch --ref main -f mode=<mode>` – modes in
`.github/workflows/watch.yml` (normal, accounts-sync, bootstrap, fill-markets, reset-pending, relayout, relink,
hook-lab, setup-notion, test-notify, test-claude, …). One run at a time: a newer pending dispatch cancels an older
pending one – wait until the queue is empty. Offline tests: `python3 -m pytest -q tests`.

## Formats added by hand
`add_format` input (Run workflow): TikTok links of any app; first = example. Judged/built/published like a viral video,
every given video counts for the ranking, its creators are followed from then on (status manual, never paused or
blocked). The app's name goes into config.json `other_apps` (regex) so it is replaced/counted like Astra AI
(Studyflash is there). A failed add alerts and turns the run red. TikTok subtitles: the original ASR track is used,
never TikTok's machine translation.

Options per hand-added format: `registry/hand_formats.json`, keyed by the example video's id – `only_markets`
(e.g. `["sl"]`: only the Slovenian list, used for our own Slovenian creators' videos), `app_link` (the format's own page
on memoai.eu that creators film, e.g. memoai.eu/ugc/oral-quiz), `brief` (note from the campaign team for the script
writer and every check), `own_brand` (example is already a Memo AI video → the note under it doesn't say "another
brand"). Several formats in one run: separate them with `;` in the add_format input.

## Ranking (user's rule, 11 Oct 2026)
Hot formats (5+ viral in 7 days) first; then most viral videos (100k+) in the last 7 days; on a tie, most viral
videos in the last 30 days; then current form (`rank.order`). A format's own source video always counts for it.

## Materials
Images for a format's 🔧 materials section (e.g. screenshots cut from the original video): put them in
`registry/materials/<format id>/<market>/*.png` and run `mode=add-materials target=<format id>` (once per page).

## Note under the inspiration video (user's wording, 10 Oct 2026)
The ⚠️ callout says: the inspiration video is from another brand and is NOT the video to make – copy only the overall
vibe, camera angles, how it's filmed, editing and where the demos are (that's what inspiration videos are for); the
second line says to swap the other app for Memo AI. `mode=renote` puts the current text on every page; `verify`
checks it.

## All scripts in one file
`mode=export` writes every format page (title, script with cues, visual hook) as Markdown, encrypted with
registry/export_cert.pem, to state/scripts_export.enc (repo and logs are public). Decrypt on the Mac with
`scripts/read_export.sh` (private key: ~/.config/memo-viral-watch/export_key.pem - never commit it).

## Check everything
`mode=verify` (read-only): every list (order, numbering, layout), live page (video, sections, links), held page
(staging) and both hook labs against the state; also lists leftover staging pages (never deletes).

## Status (11 Oct 2026)
Balkan list 14 formats, Slovenian list 18 (4 Slovenian-only from our own Memo AI creators), verify clean. Approved
(locked) scripts: the oral-quiz format "Nisam stvorena za sestrinstvo" (sl + sh, memoai.eu/ugc/oral-quiz) and "Faze
srednje šole" (sl). Archived after full retries: Mozak premium, Gradivo kao sočan trač. @studywithpija's video was
unavailable (not added). Open: Discord server logo (user). The Claude subscription is shared with the JobStep watcher.
