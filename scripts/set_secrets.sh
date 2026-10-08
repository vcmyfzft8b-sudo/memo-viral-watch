#!/bin/zsh
# Run this yourself once: copies the keys that are the SAME as for JobStep (Soniox speech-to-text, Lightreel search)
# from your local .env files into this repo's GitHub secrets, and makes a new private ntfy topic for phone pushes.
# Notion, Slack and Claude are saved with their own scripts (scripts/save_*.sh). Nothing is printed except the topic.
set -e
REPO="${1:-vcmyfzft8b-sudo/memo-viral-watch}"

get() {  # get <file> <KEY>
  grep -E "^[[:space:]]*(export[[:space:]]+)?$2[[:space:]]*=" "$1" | tail -1 | sed -E "s/^[[:space:]]*(export[[:space:]]+)?$2[[:space:]]*=[[:space:]]*//; s/^[\"']//; s/[\"'][[:space:]]*$//"
}

get ~/Documents/transcript/.env.local               SONIOX_API_KEY    | gh secret set SONIOX_API_KEY    -R "$REPO"
get ~/Documents/auto-outreach-parakeetai/.env.local LIGHTREEL_API_KEY | gh secret set LIGHTREEL_API_KEY -R "$REPO"

TOPIC="memo-radar-$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | head -c 20)"
echo -n "$TOPIC" | gh secret set NTFY_TOPIC -R "$REPO"

echo "Secrets set for $REPO."
echo "Optional phone pushes: install the ntfy app (iOS/Android) and subscribe to this topic:"
echo "  $TOPIC"
echo "(keep it private – anyone with the topic name can read the alerts)"
