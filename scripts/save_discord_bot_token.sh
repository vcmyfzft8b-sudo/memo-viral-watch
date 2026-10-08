#!/bin/zsh
# Optional (off in config.json): saves the Discord bot token (Developer Portal -> Bot -> Reset Token -> Copy).
REPO="${1:-vcmyfzft8b-sudo/memo-viral-watch}"
TOKEN="$(pbpaste | tr -d '[:space:]')"
if [[ ${#TOKEN} -lt 50 || "$TOKEN" != *.*.* ]]; then
  echo "❌ No bot token in the clipboard. In the Developer Portal under 'Bot' click 'Reset Token' -> 'Copy' and run again."; exit 1
fi
printf '%s' "$TOKEN" | gh secret set DISCORD_BOT_TOKEN -R "$REPO" && echo "✅ Discord bot connected – tell Claude: done"
printf '' | pbcopy
