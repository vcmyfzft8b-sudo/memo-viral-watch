"""Keep the list of Astra AI creator accounts in the Balkans complete (runs every few days).

- Lightreel (LIGHTREEL_API_KEY) is asked for every account promoting Astra AI in Serbia, Croatia, Bosnia and
  Herzegovina and Montenegro; new handles are verified with TikTok's creator embed: posted in the last 30 days AND
  Astra AI in their captions or videos; then Claude reads their latest videos: really Astra AI UGC, and in
  Serbo-Croatian (Slovenian accounts - Astra AI's home market - are not ours to watch).
- Accounts that stop posting Astra AI content for 30 days are paused (not fetched every 6 h) and re-checked
  on every discovery run, so they come back automatically.
"""
import os
import re
import time

import requests

from . import tiktok
from .brand import SOURCE, SOURCE_DESC, SOURCE_TAGS, says_source
from .markets import TEXT

PRIMARY_LANG = next(iter(TEXT))  # the market language (Serbo-Croatian)

QUESTION = f"""Today is {{today}}. Give me a COMPLETE list of every TikTok account that posted sponsored, affiliate or
creator-program videos for {SOURCE_DESC} in the last 30 days, in Serbia, Croatia, Bosnia and Herzegovina or Montenegro
(videos in Serbian, Croatian, Bosnian or Montenegrin). Include students, study/school creators and normal
lifestyle creators too. Be exhaustive. Already known (you may skip them): {{known}}
Answer with one line per account exactly like: ACCOUNT | @handle | market"""


SPOKEN = {}  # handle -> speech of its most-viewed recent videos that names the app (filled by spoken_mention)


def spoken_mention(handle, vids=None, n=2, max_days=30):
    """Many Astra AI creators only SAY the app's name (or show it on screen) - no caption, no on-screen text, no TikTok
    subtitles. Their most-viewed recent videos are transcribed (Soniox); returns the speech that names the app, or ''."""
    import shutil
    import tempfile
    from . import media, soniox
    vids = vids if vids is not None else tiktok.latest_videos(handle)
    recent = [v for v in vids if (time.time() - (int(v['id']) >> 32)) / 86400 <= max_days]
    for v in sorted(recent, key=lambda v: -v['views'])[:n]:
        work = tempfile.mkdtemp(prefix='speech-')
        try:
            url = f"https://www.tiktok.com/@{handle}/video/{v['id']}"
            text = soniox.transcribe(media.audio(media.download(url, work), work)).get('text', '')
        except Exception as e:
            print('speech check failed', handle, v['id'], str(e)[:120])
            text = ''
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if says_source(text):
            SPOKEN[handle] = text[:1200]
            return text
    return ''


def check_account(handle, max_days=30, listen=True):
    """'active', 'inactive' or 'invalid' for one TikTok account. Active = posted in the last 30 days AND the app is
    named in a caption, on-screen text or subtitles - or, failing that, in the speech of its most-viewed recent videos."""
    vids = tiktok.latest_videos(handle)
    if not vids:
        return 'invalid'
    newest = max(int(v['id']) >> 32 for v in vids)
    recent = (time.time() - newest) / 86400 <= max_days
    found = any(says_source(v['desc']) for v in vids)
    if not found:  # the app often only appears on screen or in speech: read up to 8 videos
        for v in vids[:8]:
            d = tiktok.video_detail(handle, v['id'])
            if d and says_source(' '.join([d['desc'], d['sticker'], d['subtitles']])):
                found = True
                break
    if recent and not found and listen and os.environ.get('SONIOX_API_KEY'):
        found = bool(spoken_mention(handle, vids, max_days=max_days))
    return 'active' if (recent and found) else 'inactive'


# One Lightreel question per country finds far more accounts than one question for the whole region.
MARKETS = ['Serbia', 'Croatia', 'Bosnia and Herzegovina', 'Montenegro']
MARKET_HINT = ("\nOnly look at this market: {market}. Search captions, hashtags (" + SOURCE_TAGS + "), on-screen text and "
               "spoken mentions. List only accounts NOT in the known list.")


def _ask(key, q):
    try:
        r = requests.post('https://api.lightreel.ai/v1/chat', json={'question': q}, timeout=1500,
                          headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        return r.json().get('answer', '') if r.ok else ''
    except (requests.RequestException, ValueError):
        return ''


UGC_SYSTEM = "You check TikTok accounts for a marketing team. Reply with JSON only."


def account_text(handle, details=4):
    """The account's latest videos as text: caption for all, plus on-screen text and speech for the newest few."""
    vids = tiktok.latest_videos(handle)[:8]
    lines = []
    for i, v in enumerate(vids):
        line = f"- ({round((time.time() - (int(v['id']) >> 32)) / 86400)}d ago, {v['views']} views) CAPTION: {v['desc'][:220]}"
        if i < details:
            d = tiktok.video_detail(handle, v['id'])
            if d:
                line += f" | ON SCREEN: {d['sticker'][:160]} | SPEECH: {d['subtitles'][:300]}"
        lines.append(line)
    if SPOKEN.get(handle):
        lines.append(f"- SPEECH of one of its most-viewed recent videos (transcribed): {SPOKEN[handle][:900]}")
    return '\n'.join(lines)


def confirm_ugc(handles, model='sonnet', batch=8, details=4):
    """Claude reads each account's latest videos: is it really a UGC/creator account promoting Astra AI, and in which
    language does it post? Returns {handle: {'verdict': 'source_ugc'|'other_app'|'not_ugc'|'unclear', 'other_app',
    'language', 'reason'}}."""
    import concurrent.futures as cf
    from . import llm
    with cf.ThreadPoolExecutor(8) as ex:
        texts = dict(zip(handles, ex.map(lambda h: account_text(h, details), handles)))
    out = {}

    def one(chunk):
        blocks = '\n\n'.join(f"ACCOUNT @{h}\n{texts[h] or '(no videos)'}" for h in chunk)
        prompt = f"""Each block below is a TikTok account with its latest videos (newest first).
Decide for each account: is it a UGC / creator account that currently promotes {SOURCE_DESC} - i.e. it posts
(sponsored, affiliate or creator-program) videos where the {SOURCE} app is shown, recommended or named?
{SOURCE}'s own brand accounts also count.
- "source_ugc": yes, it promotes the {SOURCE} app (at least one recent video clearly does).
- "other_app": a study/school creator account that now promotes a DIFFERENT app (name it), not {SOURCE}.
- "not_ugc": a random/personal account, or "astra" only appears as a normal word / another product (e.g. a car,
  a flower, a company), not the study app.
- "unclear": not enough information.
Also give the main language the account speaks/writes in (English name, e.g. "Croatian", "Serbian", "Bosnian",
"Slovenian", "German").

{blocks}

Return JSON {{"results": [{{"handle": "<handle without @>", "verdict": "...", "other_app": "<name or empty>",
"language": "<language>", "reason": "<short, in English>"}}]}}"""
        try:
            return llm.chat_json(model, UGC_SYSTEM, prompt, timeout=900).get('results', [])
        except Exception as e:
            print('UGC check failed:', str(e)[:200])
            return []

    with cf.ThreadPoolExecutor(3) as ex:
        for results in ex.map(one, [handles[i:i + batch] for i in range(0, len(handles), batch)]):
            for x in results:
                out[str(x.get('handle', '')).lstrip('@').lower()] = x
    return out


def lightreel_handles(known, question=None, hint=None):
    """Handles Lightreel names for every market (asked in parallel), minus nothing - the caller filters known ones."""
    import concurrent.futures as cf
    key = os.environ.get('LIGHTREEL_API_KEY')
    if not key:
        return set()
    q = (question or QUESTION).format(today=time.strftime('%d %B %Y'), known=', '.join('@' + h for h in sorted(known)))
    with cf.ThreadPoolExecutor(6) as ex:
        answers = list(ex.map(lambda m: _ask(key, q + (hint or MARKET_HINT).format(market=m)), MARKETS))
    return {h.lower().rstrip('.') for a in answers for h in re.findall(r'@([A-Za-z0-9._]{2,30})', a)}


def regional(handle, verdict=None):
    """Does the account post in Serbo-Croatian (our region)? Claude's language verdict first, the captions second."""
    from .markets import lang_matches
    said = (verdict or {}).get('language')
    if said:
        return lang_matches(PRIMARY_LANG, said)
    return language(handle) == PRIMARY_LANG


def refresh(accounts):
    """accounts: {handle: {'status': 'active'|'inactive'|'manual', 'since': ts, ...}} -> (accounts, added, paused, revived)."""
    added, paused, revived = [], [], []
    new = [h for h in sorted(lightreel_handles(set(accounts)) - set(accounts)) if check_account(h) == 'active']
    verdicts = confirm_ugc(new) if new else {}
    for h in new:  # only real Astra AI UGC accounts from our region (Claude read their latest videos)
        v = verdicts.get(h, {})
        if v.get('verdict') == 'source_ugc' and regional(h, v):
            accounts[h] = {'status': 'active', 'since': int(time.time()), 'source': 'lightreel', 'checked_ugc': True,
                           'lang': PRIMARY_LANG}
            added.append(h)
        elif v.get('verdict') == 'source_ugc':  # Astra AI creator, but not from our region: remembered, never watched
            accounts[h] = {'status': 'inactive', 'since': int(time.time()), 'source': 'lightreel', 'blocked': True,
                           'blocked_reason': f"outside the region ({v.get('language') or '?'})"}
    for h, info in accounts.items():
        if info['status'] == 'manual' or h in added or info.get('blocked'):
            continue  # manually confirmed creators are always tracked; blocked = not Astra AI UGC or not our region
        status = check_account(h)
        if status == 'invalid':
            continue
        if info['status'] == 'active' and status == 'inactive':
            info['status'] = 'inactive'
            paused.append(h)
        elif info['status'] == 'inactive' and status == 'active':
            info['status'] = 'active'
            revived.append(h)
        info['checked'] = int(time.time())
    return accounts, added, paused, revived


def language(handle):
    """Our market language ('sh') if the account's captions are mostly Serbo-Croatian, 'sl' for Slovenian, else ''."""
    from .markets import SLOVENIAN_STOPWORDS, TEXT
    words = re.findall(r"[a-zčćđšžäöüßàâçéèêëîïôûùÿœñáíóú’']+", ' '.join(v['desc'] for v in tiktok.latest_videos(handle)).lower())
    if not words:
        return ''
    tables = {lang: set(t['stopwords'].split()) for lang, t in TEXT.items()}
    tables['sl'] = SLOVENIAN_STOPWORDS
    scores = {lang: sum(w in stop for w in words) / len(words) for lang, stop in tables.items()}
    # words only one of the two uses decide between Serbo-Croatian and Slovenian (both have "je", "da", "se", ...)
    only_sl = sum(w in ('in', 'so', 'ki', 'kaj', 'tudi', 'zelo', 'jaz', 'sploh', 'lahko') for w in words)
    only_sh = sum(w in ('i', 'su', 'koji', 'koja', 'što', 'šta', 'jer', 'već', 'ovo', 'ovaj', 'evo') for w in words)
    best = max(scores, key=scores.get)
    if best != 'sl' and only_sl > only_sh:
        best = 'sl'
    elif best == 'sl' and only_sh > only_sl:
        best = next(iter(TEXT))
    return best if scores[best] >= 0.08 else ''
