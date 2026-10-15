# Memo AI viral watch

The same watcher as *JobStep viral watch*, separate in every way (own repo, own Notion workspace, own Slack app,
own state): it watches **Astra AI** creators in the **Balkans** (Serbia, Croatia, Bosnia and Herzegovina,
Montenegro) and turns their viral formats into **Memo AI** creator pages in **Serbo-Croatian** (Latin script,
ijekavian, words the whole region understands).

Every 6 hours (GitHub Actions) it:

1. **Pulls every new video** of all active Astra AI creator accounts (`state/accounts.json` on the `state` branch)
   and keeps each video on a 7-day watchlist.
2. **Re-checks every watchlist video** (views, likes, shares, saves) and stores a snapshot.
3. **Alerts** you in a **Discord channel just for this watcher** (Slack personal messages also work if set up),
   optional phone push via ntfy, + a log line on the private Notion page *Viral-Radar (interno)*:
   - 🟡 **taking off** – 5k views within 6 h, 20k within 24 h, 50k within 48 h, or 10× the creator's usual views
   - 🟢 **viral** – 100k+ views within 7 days (20 of 269 recent Balkan Astra AI videos got there, 8 Oct 2026)
   - 💾 **converting** – 30k+ views, 300+ saves and 2%+ of viewers saved it (below the viral bar)
   - saves decide (user's rule, 15 Oct 2026, replaces "only views" of 10 Oct): the list holds formats that convert best
     AND still go viral. A viral video saved by fewer than 0.5% of viewers still alerts and counts for its format, but
     never builds or brings back one (`watcher/conversion.py`, settings in `config.json` → `conversion`)
4. **Builds a new format page** when a viral video with enough saves, or a converting one, uses a format that is not in
   the list yet:
   download → Soniox transcription → frames → Claude writes the page (Astra AI → Memo AI, a Memo AI link at every app
   moment, title, visual hook, materials) → automatic checks (no "Astra", Latin script only, ijekavian, length within
   80–110 %, only real Memo AI features – `watcher/brand.py`) → Notion page → added to the list at its ranked position.
5. **Order of the list**: hot formats first (5+ viral in 7 days AND saved at least like an average format), then by
   conversion score = how many viewers save the format's videos (vs an average format) × how well it goes viral
   (square root). `mode=conversion` prints the board (and reads saves of older videos right away); every run reads 60.
6. **Every 3 days – complete account list**: Lightreel is asked for every Astra AI account per country; each new handle
   is checked on TikTok (posted in the last 30 days + Astra AI in captions or videos) and by Claude (really Astra AI
   UGC, and Serbo-Croatian – Slovenian accounts are skipped). Accounts without Astra AI posts for 30 days are paused.
7. **Weekly (Monday)**: re-ranks the list, takes formats out that do not convert (score below 0.9 once 2+ videos have
   saves – going viral does not protect them; archive, nothing deleted; `mode=lineup` shows the plan), Slack report.
   An archived format comes back only when a new video of it goes viral/converts AND is saved like a typical video.

Our own Memo AI creators (to see how each format does for us) are read from Megasheet once a Memo AI campaign exists –
put its name in `config.json` → `"megasheet": {"campaigns": {"<name>": "sh"}}` and run `./scripts/save_megasheet_login.sh`.
Until then they are found via Lightreel (#memoai) and `registry/own_seed.json`.

## Setup (once)

| Step | How |
|---|---|
| Soniox, Lightreel, ntfy (same keys as JobStep) | `./scripts/set_secrets.sh` |
| Claude (your subscription, never the API) | `claude setup-token`, then `./scripts/save_claude_token.sh` |
| Notion (the NEW workspace) | integration "Memo Radar" + one page connected to it, copy its secret, `./scripts/save_notion_token.sh` |
| Discord alerts | channel → Edit → Integrations → Webhooks → "Memo Radar" → Copy Webhook URL, `./scripts/save_discord_alerts.sh` |
| Slack (optional, personal messages) | Slack app "Memo Radar", copy its bot token (`xoxb-…`), `./scripts/save_slack.sh` |
| Notion pages | Actions → Run workflow → `setup-notion` (builds list, all formats, archive, hook lab, radar) |
| Creators | `accounts-sync` (checks the Lightreel candidates in `registry/accounts_sync.json`) |
| First formats | `bootstrap` (turns the strongest viral videos of the last 30 days into pages; run again to continue) |
| Check | `test-notify` (Discord), `test-claude`, `dry-run` |

## Run manually

GitHub → Actions → *Memo AI viral watch* → Run workflow. Locally: `STATE_DIR=/tmp/state python -m watcher.main --dry-run`.

Offline tests (no Notion, Claude or other live calls): `python -m pytest -q tests`

## Files

- `watcher/brand.py` – who is who (Astra AI → Memo AI), what Memo AI can and cannot do (checked against the app code)
- `watcher/markets.py` – the Balkan market: every text on the pages, language rules (ijekavian, Latin)
- `watcher/discover.py` – finding Astra AI creators (Lightreel, TikTok, Claude), region filter
- `watcher/tiktok.py` – creator embed (latest videos) + video page (stats, on-screen text, subtitles)
- `watcher/detect.py` – taking off / viral rules
- `watcher/classify.py` – existing format or new one (Claude)
- `watcher/builder.py` – page spec + checks · `watcher/notion.py` – page layout, list · `watcher/setup.py` – Notion setup
- `watcher/audit.py`, `watcher/crosscheck.py`, `watcher/gate.py` – quality checks before anything reaches creators
- `watcher/notify.py` – Discord alerts channel, Slack (optional), ntfy, radar log
- `registry/` – formats, reviewed references, approved scripts (empty at the start), example pages in our layout

The code keeps the multi-market shape of the JobStep watcher: another market can be added in `config.json` and
`watcher/markets.py` (one shared format list, one page per market).
