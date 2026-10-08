"""Notifications: a Discord channel just for this watcher (DISCORD_ALERTS_WEBHOOK_URL), optional phone push via
ntfy (NTFY_TOPIC), plus a log line on the private Notion radar page.

Slack still works too if its secrets are set (SLACK_BOT_TOKEN + SLACK_USER_ID for personal messages, or
SLACK_WEBHOOK_URL) - every message goes to every channel that is set up.
"""
import os
import re
import time

import requests

from . import notion

DISCORD_LIMIT = 1900  # Discord allows 2000 characters per message


def _discord_text(text):
    """Slack formatting -> Discord: <url|label> -> [label](<url>), *bold* -> **bold**, _italic_ stays."""
    text = re.sub(r'<(https?://[^|>]+)\|([^>]+)>', lambda m: f'[{m.group(2)}](<{m.group(1)}>)', text)
    text = re.sub(r'<(https?://[^>]+)>', r'<\1>', text)
    return re.sub(r'(?<![*\w])\*([^*\n]+)\*(?![*\w])', r'**\1**', text)


def _chunks(text, size=DISCORD_LIMIT):
    out, cur = [], ''
    for line in text.split('\n'):
        while len(line) > size:
            out.append(cur) if cur else None
            cur = ''
            out.append(line[:size])
            line = line[size:]
        if len(cur) + len(line) + 1 > size:
            out.append(cur)
            cur = ''
        cur = f'{cur}\n{line}' if cur else line
    return [c for c in out + [cur] if c.strip()]


def discord(title, message, click=None):
    url = os.environ.get('DISCORD_ALERTS_WEBHOOK_URL')
    if not url:
        return
    text = _discord_text(f'*{title}*\n{message}' + (f'\n<{click}|▶ Open>' if click else ''))
    for part in _chunks(text):
        for _ in range(3):
            try:
                r = requests.post(url, json={'content': part, 'username': 'Memo Radar', 'allowed_mentions': {'parse': []},
                                             'flags': 4}, timeout=20)  # 4 = no link previews
            except requests.RequestException:
                break
            if r.status_code == 429:  # rate limited: wait as Discord says, then try again
                time.sleep(float((r.json() if r.content else {}).get('retry_after', 2)) + 0.5)
                continue
            break


def slack(title, message, click=None):
    text = f'*{title}*\n{message}' + (f'\n<{click}|▶ Open>' if click else '')
    bot, user = os.environ.get('SLACK_BOT_TOKEN'), os.environ.get('SLACK_USER_ID')
    try:
        if bot and user:  # a message to a user id lands in the app's direct messages with that user
            r = requests.post('https://slack.com/api/chat.postMessage', timeout=20,
                              headers={'Authorization': f'Bearer {bot}'},
                              json={'channel': user, 'text': text, 'unfurl_links': False, 'unfurl_media': False})
            if not r.json().get('ok'):
                print('slack failed:', r.json().get('error'))
        elif os.environ.get('SLACK_WEBHOOK_URL'):
            requests.post(os.environ['SLACK_WEBHOOK_URL'], json={'text': text, 'unfurl_links': False}, timeout=20)
    except (requests.RequestException, ValueError):
        pass


def slack_configured():
    return bool(os.environ.get('DISCORD_ALERTS_WEBHOOK_URL') or (os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_USER_ID'))
                or os.environ.get('SLACK_WEBHOOK_URL'))


def push(title, message, click=None, tags=''):
    discord(title, message, click)
    slack(title, message, click)
    topic = os.environ.get('NTFY_TOPIC')
    if not topic:
        return
    headers = {'Title': title.encode('utf-8'), 'Tags': tags, 'Priority': 'high'}
    if click:
        headers['Click'] = click
    try:
        requests.post(f'https://ntfy.sh/{topic}', data=message.encode('utf-8'), headers=headers, timeout=20)
    except requests.RequestException:
        pass


def radar(radar_page, text, link=None, link_label=None):
    if not radar_page:
        return
    rich = [notion.rt(text)]
    if link:
        rich.append(notion.rt(' ' + (link_label or 'Link'), link=link))
    try:
        notion.append_log(radar_page, rich)
    except RuntimeError as e:
        print('radar log failed:', str(e)[:200])
