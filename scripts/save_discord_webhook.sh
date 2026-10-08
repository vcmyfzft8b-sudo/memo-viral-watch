#!/bin/zsh
# Optional (off in config.json): saves a Discord #announcements webhook (copied in Discord) as GitHub secret
# DISCORD_WEBHOOK_URL for the "format is going viral" announcements.
REPO="${1:-vcmyfzft8b-sudo/memo-viral-watch}"
URL="$(pbpaste | tr -d '[:space:]')"
if [[ "$URL" != https://discord.com/api/webhooks/* && "$URL" != https://discordapp.com/api/webhooks/* ]]; then
  echo "❌ No Discord webhook link in the clipboard. In Discord click 'Copy Webhook URL' and run the script again."; exit 1
fi
printf '%s' "$URL" | gh secret set DISCORD_WEBHOOK_URL -R "$REPO" && echo "✅ Discord connected – tell Claude: done"
