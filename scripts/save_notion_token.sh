#!/bin/zsh
# Saves the token of the NEW Notion workspace's integration ("Memo Radar") as GitHub secret NOTION_TOKEN.
# notion.so/profile/integrations -> Memo Radar -> Internal Integration Secret -> Show -> Copy, then run this script.
# Nothing secret is printed.
REPO="${1:-vcmyfzft8b-sudo/memo-viral-watch}"
TOKEN="$(pbpaste | tr -d '[:space:]')"
if [[ "$TOKEN" != ntn_* && "$TOKEN" != secret_* ]]; then
  echo "❌ No Notion integration secret in the clipboard (it starts with ntn_). Copy it and run the script again."; exit 1
fi
printf '%s' "$TOKEN" | gh secret set NOTION_TOKEN -R "$REPO" && echo "✅ Notion connected – tell Claude: done"
printf '' | pbcopy
