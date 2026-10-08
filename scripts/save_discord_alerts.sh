#!/bin/zsh
# Saves the webhook of the Discord channel where the watcher posts its alerts (taking off, viral, new formats,
# weekly report) as GitHub secret DISCORD_ALERTS_WEBHOOK_URL. In Discord: channel -> Edit Channel -> Integrations ->
# Webhooks -> Memo Radar -> "Copy Webhook URL", then run this script. Nothing secret is printed.
REPO="${1:-vcmyfzft8b-sudo/memo-viral-watch}"
URL="$(pbpaste | tr -d '[:space:]')"
if [[ "$URL" != https://discord.com/api/webhooks/* && "$URL" != https://discordapp.com/api/webhooks/* ]]; then
  echo "❌ No Discord webhook link in the clipboard. In Discord click 'Copy Webhook URL' and run the script again."; exit 1
fi
printf '%s' "$URL" | gh secret set DISCORD_ALERTS_WEBHOOK_URL -R "$REPO" && echo "✅ Discord alerts connected – tell Claude: done"
printf '' | pbcopy
