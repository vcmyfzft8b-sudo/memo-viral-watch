"""Conversion: how many viewers SAVE a format's videos (user's rule, 15 Oct 2026).

The list must hold formats that convert best AND still go viral - not formats that only go viral. A save means a
viewer kept the video to use it later (the best free signal of real interest in the app); a like or a view does not.
In our data (224 regional study-app videos, Oct 2026) useful lists of tools / discounts / tricks with a real app demo
were saved by 2-4% of viewers, games and skits by 0.2-0.7%.

- save rate of a video = saves / views (only videos with min_views+ views and a known save count).
- conversion of a format = its videos' average save rate (recent weeks count most), pulled towards the network's
  typical save rate when it has few videos; conv = that / the network's typical rate (1.0 = an average format).
- score = conv x reach ** reach_weight, reach = rank.form (how well it goes viral right now, 1.0 = average).
  Conversion decides, reach still counts: a format that only goes viral cannot win on views alone.
- a video triggers a new format (or brings one back) when it goes viral AND enough viewers save it
  (min_save_rate), or when it is "converting": convert_views+ views, convert_min_saves+ saves and convert_save_rate+
  of its viewers saved it (so a 46k video saved by 4% counts even below the viral bar).
- hot (5+ viral in 7 days) needs conv >= hot_min_conv as well.
- weekly clean-up (lineup.py): a format with judge_min_videos+ measured videos whose score is below remove_below
  leaves the list, also when it still goes viral or is new (protected only while hot / saved like an average format).
"""
import statistics
import time

DAY = 86400

DEFAULTS = {
    'min_views': 10_000,          # a video's save rate counts from this many views on
    'min_save_rate': 0.005,       # viral videos below this never build / bring back a format
    'convert_views': 30_000,      # "converting" trigger (below the viral bar)
    'convert_save_rate': 0.02,
    'convert_min_saves': 300,
    'prior_rate': 0.006,          # typical save rate when there are too few videos to measure it
    'prior_videos': 3,            # smoothing: a format's rate counts like this many typical videos more
    'half_life_days': 30,
    'window_days': 120,
    'reach_weight': 0.5,
    'hot_min_conv': 1.0,
    'judge_min_videos': 2,        # the clean-up judges a format on saves from this many measured videos on
    'remove_below': 0.9,          # ... and takes it out below this score (1.0 = an average format)
    'rate_cap': 0.12,             # one odd video cannot carry a format
    'backfill_per_run': 60,
    'classify_per_run': 40,
}


def conf(cfg):
    return {**DEFAULTS, **(cfg or {}).get('conversion', {})}


def known(v):
    """True when the video's save count was really read. A views-only check (detail_missing) is unknown: a new
    watchlist video starts with saves 0, and its newer views would not match older saves anyway."""
    return v.get('saves') is not None and not v.get('saves_unknown') and not v.get('detail_missing')


def save_rate(v):
    """saves / views (None when the save count is unknown or there are no views)."""
    if not known(v) or not v.get('views'):
        return None
    return v['saves'] / v['views']


def measured_rate(v, c):
    r = save_rate(v)
    if r is None or v['views'] < c['min_views']:
        return None
    return min(r, c['rate_cap'])


def record(entry, v, old=None):
    """Copies likes/saves/shares into a history entry - only when they were really read (a views-only check keeps the
    last real numbers)."""
    old = old or {}
    if v.get('detail_missing') or v.get('saves') is None:
        for k in ('likes', 'saves', 'shares'):
            if k in old:
                entry[k] = old[k]
        return entry
    for k in ('likes', 'saves', 'shares'):
        entry[k] = int(v.get(k) or 0)
    entry['saves_unknown'] = False  # read now (an older failed read must not stick when entries are merged)
    return entry


def baseline(history, c, now=None):
    """The network's typical save rate (median of measured videos in the window); prior_rate with < 10 videos."""
    now = now or time.time()
    rates = [r for v in history.values() if now - v.get('created', 0) <= c['window_days'] * DAY
             for r in [measured_rate(v, c)] if r is not None]
    return statistics.median(rates) if len(rates) >= 10 else c['prior_rate']


def board(history, formats, cfg, now=None, reach=None):
    """{format_id: {'rate', 'conv', 'reach', 'score', 'videos', 'raw_rate'}} for every format (list and archive) and
    the network's typical rate. reach: rank.form() output (None -> 1.0 for everyone)."""
    c = conf(cfg)
    now = now or time.time()
    p0 = max(baseline(history, c, now), 1e-4)
    k = c['prior_videos']
    per = {}
    for v in history.values():
        if not v.get('format') or now - v.get('created', 0) > c['window_days'] * DAY:
            continue
        r = measured_rate(v, c)
        if r is not None:
            per.setdefault(v['format'], []).append((0.5 ** ((now - v['created']) / DAY / c['half_life_days']), r))
    out = {}
    for f in formats:
        xs = per.get(f['id'], [])
        w = sum(x for x, _ in xs)
        rate = (sum(x * r for x, r in xs) + p0 * k) / (w + k)
        conv = rate / p0
        rch = max((reach or {}).get(f['id'], {}).get('form', 1.0), 0.05)
        out[f['id']] = {'rate': rate, 'conv': conv, 'reach': rch, 'score': conv * rch ** c['reach_weight'],
                        'videos': len(xs), 'raw_rate': (sum(x * r for x, r in xs) / w) if w else None}
    return out, p0


def converting(v, cfg):
    """A video below the viral bar that viewers save a lot (see module doc)."""
    c = conf(cfg)
    r = save_rate(v)
    return (r is not None and v.get('views', 0) >= c['convert_views'] and v.get('saves', 0) >= c['convert_min_saves']
            and r >= c['convert_save_rate'])


def too_few_saves(v, cfg):
    """Known save rate below min_save_rate (unknown -> False: never blocked on missing data)."""
    r = save_rate(v)
    return r is not None and r < conf(cfg)['min_save_rate']


def worth_building(v, cfg):
    """Viral with enough saves, or converting."""
    viral = v.get('views', 0) >= cfg['thresholds']['viral_views']
    return (viral and not too_few_saves(v, cfg)) or converting(v, cfg)


def pct(r):
    return '?' if r is None else f'{r * 100:.1f}%'


def backfill(history, limit, now=None, detail=None, min_views=10_000, days=120):
    """Reads likes/saves of older history videos that were stored before saves were kept (newest first, limit per
    run). Returns the fresh details of the updated videos (for sorting them into formats; their text is not kept in
    history). detail: (handle, id) -> video detail or None (tiktok.video_detail)."""
    if detail is None:
        from .tiktok import video_detail as detail
    now = now or time.time()
    todo = sorted([(vid, v) for vid, v in history.items() if 'saves' not in v and not v.get('saves_unknown')
                   and v.get('views', 0) >= min_views and now - v.get('created', 0) <= days * DAY],
                  key=lambda x: -x[1]['created'])[:limit]
    done = []
    for vid, v in todo:
        d = detail(v['handle'], vid)
        if not d:
            v['saves_tries'] = v.get('saves_tries', 0) + 1
            if v['saves_tries'] >= 3:
                v['saves_unknown'] = True
            continue
        v['views'] = max(v.get('views', 0), d['views'])
        record(v, d)
        v.pop('saves_tries', None)
        done.append({**d, 'id': vid})
    return done


def to_sort(history, details):
    """Backfilled videos no check has put into a format yet (judged ones keep their verdict)."""
    return [d for d in details if not history[d['id']].get('format') and not history[d['id']].get('judged')
            and not history[d['id']].get('sorted')]
