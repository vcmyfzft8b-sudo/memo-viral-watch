"""Weekly clean-up: formats that do not convert leave the list (Monday, first run of the week).

User's rule (15 Oct 2026): the list holds formats that convert best and still go viral - not formats that only go
viral. Every format has a conversion score (conversion.py / rank.order: how many viewers save its videos compared
with an average format x how well it goes viral right now; 1.0 = an average format).

A format leaves the list when it is not protected and
- once conversion.judge_min_videos+ of its videos have a known save count: its score is below conversion.remove_below.
  Then neither going viral nor being new protects it - only being hot (5+ viral in 7 days that viewers also save) or a
  viral video in the last 21 days while viewers save it at least like an average format;
- with fewer measured videos: its current form (reach) is below lineup.remove_below, no viral video in the last 21
  days and it came into the list more than lineup.protect_days ago (like before).
Formats removed by the user never come back on their own.
The list never shrinks below lineup.min_formats (the weakest leave first).

Per market (user's rule, 16 Oct 2026): only markets with "cleanup": true in config.json are cleaned (the Balkan list
keeps only the highest-converting formats); the others keep every format (Slovenia: its formats convert there).
Leaving = the format's page in each cleaned market moves to that market's archive (nothing is deleted); it stays in
the other markets' lists (only_markets) - or is archived when no list keeps it. Formats come INTO the lists when a
video goes viral with enough saves or converts (main.handle_viral): new ones are built, archived ones come back, and
a format the clean-up took out of a market comes back into that market the same way.
"""
import datetime
import re
import time

from . import hot, notion, notify, own, rank, state

DAY = 86400


def listed_at(f):
    """When the format came into the list (0 = it has been there since before the lineup existed)."""
    if f.get('listed_at'):
        return f['listed_at']
    if (f.get('revived') or {}).get('at'):
        return f['revived']['at']
    m = re.match(r'A(\d{14})$', f['id'])  # formats built by the watcher: A + build time
    if m:
        return int(datetime.datetime.strptime(m.group(1), '%Y%m%d%H%M%S').replace(tzinfo=datetime.timezone.utc).timestamp())
    return 0


def markets_of(f, cfg):
    """The enabled markets a format is made for (config order)."""
    only = f.get('only_markets')
    return [k for k, m in cfg['markets'].items() if m.get('enabled', True) and (not only or k in only)]


def cleaned(cfg):
    """Markets the weekly clean-up works on ("cleanup": false keeps every format in that market's list)."""
    return [k for k, m in cfg['markets'].items() if m.get('enabled', True) and m.get('cleanup', True)]


def plan(history, formats, cfg, own_videos, now=None):
    """Which formats would leave: {'out': [(format, score, reason)], 'board': {...}, 'protected': {...}}."""
    from . import conversion
    lc = cfg['lineup']
    cc = conversion.conf(cfg)
    now = now or time.time()
    reach = rank.form(history, formats, cfg, own.stats(own_videos, formats, now, cfg['thresholds']['viral_views']), now)
    conv, p0 = conversion.board(history, formats, cfg, now, reach)
    recent = rank.recent_viral(history, formats, cfg)
    viral21 = {}
    for v in history.values():
        if v.get('format') and v['views'] >= cfg['thresholds']['viral_views'] and now - v['created'] <= 21 * DAY:
            viral21[v['format']] = viral21.get(v['format'], 0) + 1
    board = {fid: {**reach[fid], **conv[fid]} for fid in reach}

    def measured(f):
        return conv[f['id']]['videos'] >= cc['judge_min_videos']

    def protected(f):
        c = conv[f['id']]
        if recent.get(f['id'], 0) >= hot.MIN_VIRAL and c['conv'] >= cc['hot_min_conv']:
            return 'hot'
        if viral21.get(f['id']) and (not measured(f) or c['conv'] >= cc['hot_min_conv']):
            return f"{viral21[f['id']]} viral in the last 21 days"
        if now - listed_at(f) < lc['protect_days'] * DAY and not measured(f):
            return f"in the list for less than {lc['protect_days']} days"
        return None

    def value(f):
        return conv[f['id']]['score'] if measured(f) else reach[f['id']]['form']

    def limit(f):
        return cc['remove_below'] if measured(f) else lc['remove_below']

    def reason(f):
        c = conv[f['id']]
        if measured(f):
            return (f"saved by {conversion.pct(c['raw_rate'])} of viewers ({c['videos']} videos; typical video "
                    f"{conversion.pct(p0)}) - score {c['score']:.2f}, below {cc['remove_below']}")
        return f"current form {reach[f['id']]['form']:.2f} (below average) and no viral video in the last 21 days"

    active = [f for f in formats if f.get('status') == 'active' and set(markets_of(f, cfg)) & set(cleaned(cfg))]
    bad = sorted([f for f in active if not protected(f) and value(f) < limit(f)], key=value)
    room = max(0, len(active) - lc['min_formats'])
    out = [(f, value(f), reason(f)) for f in bad[:room]]
    return {'out': out, 'board': board, 'protected': {f['id']: protected(f) for f in active}, 'typical_rate': p0}


def apply(history, formats, cfg, own_videos, mkts, now=None):
    """Takes the badly converting formats out of the cleaned markets' lists (see the module doc). Returns the plan."""
    from . import main as watcher  # page helpers live in main
    p = plan(history, formats, cfg, own_videos, now)
    today = time.strftime('%d.%m.%Y')
    gone = []
    for f, score, reason in p['out']:
        drop = [k for k in markets_of(f, cfg) if k in cleaned(cfg)]
        keep = [k for k in markets_of(f, cfg) if k not in cleaned(cfg)]
        for mk in [mk for mk in mkts if mk['key'] in drop]:
            try:
                watcher.drop_market_page(f, mk)
            except Exception as e:
                print('clean-up: move to archive failed', mk['key'], f['title'], str(e)[:150])
        if keep:
            f['only_markets'] = keep
            f['cleaned_from'] = sorted(set(f.get('cleaned_from', [])) | set(drop))
            f.setdefault('cleanup_reason', {}).update({k: f'clean-up {today}: {reason}' for k in drop})
        else:
            f['status'] = 'archived'
            f['archived_reason'] = f'clean-up {today}: {reason}'
        flags = ' '.join(mk['T']['flag'] for mk in mkts if mk['key'] in drop)
        stays = ' '.join(mk['T']['flag'] for mk in mkts if mk['key'] in keep)
        gone.append(f"➖ *{f['title']}* – out of {flags or 'the list'}" + (f' (stays in {stays})' if stays else '') + f' – {reason}')
        state.log({'type': 'lineup_out', 'format': f['id'], 'form': round(score, 2), 'reason': reason, 'markets': drop})
    if gone:
        notify.push('🧹 Formats taken out of the list', '\n'.join(gone) +
                    '\n\n_Score 1.0 = an average format (how many viewers save it x how well it goes viral). Nothing is '
                    'deleted – they sit in the archive and come back on their own if a new video of theirs goes viral AND '
                    'gets saved._')
    return p


def due(meta, now):
    """First run of the week on Monday (UTC)."""
    week = time.strftime('%G-W%V', time.gmtime(now))
    return time.gmtime(now).tm_wday == 0 and meta.get('lineup') != week, week
