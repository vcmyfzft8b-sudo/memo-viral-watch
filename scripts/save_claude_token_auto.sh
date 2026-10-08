#!/bin/zsh
# Creates the Claude subscription token (`claude setup-token`) and saves it to GitHub right away - no copying.
# The output is recorded to a private temporary file only long enough to read the token, then deleted.
REPO="${1:-vcmyfzft8b-sudo/memo-viral-watch}"
TMP="$(mktemp -d)"; chmod 700 "$TMP"; trap 'rm -rf "$TMP"' EXIT
echo "A browser window opens: click Authorize. Then wait here."
script -q "$TMP/out" claude setup-token
TOKEN="$(/usr/bin/python3 - "$TMP/out" <<'PY'
import re, sys
t = open(sys.argv[1], errors='ignore').read()
t = re.sub(r'\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\r', '', t)
i = t.rfind('sk-ant-oat01-')
if i < 0:
    sys.exit(0)
out, newlines = [], 0
for ch in t[i:]:
    if re.match(r'[A-Za-z0-9_\-]', ch):
        out.append(ch)
        newlines = 0
    elif ch == '\n':
        newlines += 1
        if newlines >= 2:
            break
    elif ch in ' \t':
        continue
    else:
        break
token = ''.join(out)
# the terminal UI moves the cursor instead of printing new lines, so the next words ("Store this token
# securely") can run straight into the token: it always ends right before them, with "AA"
token = re.split(r'Store|Use|You', token)[0]
print(token if token.endswith('AA') else '')
PY
)"
if [[ "$TOKEN" != sk-ant-oat01-* || ${#TOKEN} -lt 100 ]]; then
  echo "❌ Could not read a complete token (length ${#TOKEN}). Run the script again."; exit 1
fi
printf '%s' "$TOKEN" | gh secret set CLAUDE_CODE_OAUTH_TOKEN -R "$REPO" && echo "✅ Claude token saved (length ${#TOKEN}) – tell Claude: done"
