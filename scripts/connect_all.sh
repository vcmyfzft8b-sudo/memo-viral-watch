#!/bin/zsh
# One script for every key the watcher needs. Run it once in the Terminal; it asks you to click "Copy" where needed.
# Every key goes from your clipboard / local .env files straight into GitHub secrets - nothing is printed or saved.
REPO="vcmyfzft8b-sudo/memo-viral-watch"
cd "$(dirname "$0")/.." || exit 1
ok() { echo "✅ $1"; }

echo "── 1/4  Soniox + Lightreel (same keys as JobStep, read from your .env files) ──"
./scripts/set_secrets.sh "$REPO" || exit 1

echo ""
echo "── 2/4  Notion ──"
echo "In the app's browser pane, Notion tab (Memo Radar → Configuration → API token): click the COPY icon next to the token."
echo "Then press Enter here."
read -r _
./scripts/save_notion_token.sh "$REPO" || exit 1

echo ""
echo "── 3/4  Discord alerts ──"
echo "In the browser pane, Discord tab (#astra-alerts → Integrations → Webhooks → Memo Radar): click 'Copy Webhook URL'."
echo "Then press Enter here."
read -r _
./scripts/save_discord_alerts.sh "$REPO" || exit 1

echo ""
echo "── 4/4  Claude (your subscription) ──"
echo "A browser window opens: click Authorize. Then the terminal shows a long token (sk-ant-oat01-…)."
claude setup-token
./scripts/save_claude_token.sh "$REPO" || exit 1

echo ""
ok "All keys saved. Tell Claude: done"
