"""Notifications: Slack to the user's PERSONAL messages (not a group channel), optional phone push via ntfy
(NTFY_TOPIC), plus a log line on the private Notion radar page.

Slack, either way works:
  SLACK_BOT_TOKEN + SLACK_USER_ID  the "Memo Radar" Slack app writes to you directly (Messages tab of the app)
  SLACK_WEBHOOK_URL                an Incoming Webhook that posts into your own direct messages
"""
import os

import requests

from . import notion


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
    return bool((os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_USER_ID')) or os.environ.get('SLACK_WEBHOOK_URL'))


def push(title, message, click=None, tags=''):
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
