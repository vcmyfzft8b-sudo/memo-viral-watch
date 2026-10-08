#!/bin/zsh
# Saves how the watcher reaches you in Slack - as a PERSONAL message, not in a group channel.
# Copy ONE of these, then run this script:
#   a) the Bot User OAuth Token of the "Memo Radar" Slack app (starts with xoxb-)  -> recommended: messages come from the app
#   b) an Incoming Webhook URL (https://hooks.slack.com/...) that posts into your own direct messages
# Nothing secret is printed.
REPO="${1:-vcmyfzft8b-sudo/memo-viral-watch}"
CLIP="$(pbpaste | tr -d '[:space:]')"
if [[ "$CLIP" == xoxb-* ]]; then
  printf '%s' "$CLIP" | gh secret set SLACK_BOT_TOKEN -R "$REPO" || exit 1
  printf '' | pbcopy
  echo "✅ Bot token saved. Now in Slack: click your profile picture -> Profile -> ⋮ (three dots) -> 'Copy member ID'."
  echo "   Then press Enter here."
  read -r _
  ID="$(pbpaste | tr -d '[:space:]')"
  if [[ "$ID" != U* || ${#ID} -lt 8 ]]; then echo "❌ That is not a member ID (it starts with U). Run the script again."; exit 1; fi
  printf '%s' "$ID" | gh secret set SLACK_USER_ID -R "$REPO" && echo "✅ Slack connected (personal messages) – tell Claude: done"
elif URL="$(pbpaste | grep -o 'https://hooks.slack.com/services/[A-Za-z0-9/]*' | head -1)"; [[ -n "$URL" ]]; then
  printf '%s' "$URL" | gh secret set SLACK_WEBHOOK_URL -R "$REPO" && echo "✅ Slack webhook saved – tell Claude: done"
  printf '' | pbcopy
else
  echo "❌ No Slack bot token (xoxb-…) or webhook link in the clipboard. Copy it and run the script again."; exit 1
fi
