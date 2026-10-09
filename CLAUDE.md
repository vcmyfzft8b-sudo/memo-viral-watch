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

## Where things are
- Who is who + real Memo AI features: `watcher/brand.py` (checked against the Memo AI app code). Market texts and
  language rules: `watcher/markets.py`.
- Notion (separate workspace, free plan → uploads ≤ 5 MiB, `watcher/media.py` compresses): root "Memo AI – TikTok
  formati", one guide page per market (list "👉 … (OBAVEZNO/OBVEZNO)" laid out 1:1 like the Parakeet list, all formats,
  archive, Visual Hook Lab = copy of Parakeet's, translated). Page ids: `state/notion.json`.
- App links on pages → https://memoai.eu/creator (user's choice); creators SAY memoai.eu.
- Engagement bar 0.75 % shares+saves (user's choice; Balkan viral videos average ~1.2 %).
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

## Check everything
`mode=verify` (read-only): every list (order, numbering, layout), live page (video, sections, links), held page
(staging) and both hook labs against the state; also lists leftover staging pages (never deletes).

## Status (10 Oct 2026)
41 followed creators (40 Astra AI + @lern.mit.domi for the Studyflash format). 7 live formats in both lists
(BCS + SLO), verify clean; 3 archived after 4 failed checks (come back if they go viral again).
Open: Discord server logo (user uploads Downloads/astra-ai-logo.png); keep or drop @creatortipsbymonika (Astra's
recruiter account); 2 leftover pages in the private staging area from a failed Studyflash attempt (trash only with
the user's OK). The Claude subscription is shared with the JobStep watcher – heavy days can hit its limit.
