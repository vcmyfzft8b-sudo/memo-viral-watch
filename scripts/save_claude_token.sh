#!/bin/zsh
# Saves the Claude subscription token (from `claude setup-token`) to GitHub, taking it from the clipboard.
# The token is never printed. Removes line breaks and checks it is complete before saving.
REPO="${1:-vcmyfzft8b-sudo/memo-viral-watch}"
echo "1) In the terminal, select the WHOLE token (sk-ant-oat01-… including the second line) and copy it (Cmd+C)."
echo "2) Then press Enter here."
read -r _
TOKEN="$(pbpaste | tr -d '[:space:]')"
if [[ "$TOKEN" != sk-ant-oat01-* || ${#TOKEN} -lt 100 ]]; then
  echo "❌ The clipboard has no complete token (length ${#TOKEN}). Copy both lines and run the script again."
  exit 1
fi
printf '%s' "$TOKEN" | gh secret set CLAUDE_CODE_OAUTH_TOKEN -R "$REPO" && echo "✅ Token saved (length ${#TOKEN}) – tell Claude: done"
printf '' | pbcopy
