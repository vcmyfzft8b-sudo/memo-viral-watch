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

## Status (9 Oct 2026)
39 active Astra AI creators; 9 formats with both pages (5 live, 4 in the quality check – decided within 1–2 runs).
Open: Discord server logo (user uploads Downloads/astra-ai-logo.png); keep or drop @creatortipsbymonika (Astra's
recruiter account) – user to decide.
