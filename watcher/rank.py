"""Order of the formats on a market's list (user's rule, 15 Oct 2026 - replaces the views-only order of 11 Oct).

The list holds formats that CONVERT best and still go viral (conversion.py):
1. Hot formats first: 5+ confirmed viral videos in the last 7 days AND their viewers save them at least like an
   average format (conversion.hot_min_conv). A format that only goes viral is not hot.
2. Then by conversion score = conv x reach ** reach_weight: conv = how many viewers save its videos compared with an
   average format (recent weeks count most, few videos -> pulled towards average), reach = current form (form() below:
   how likely one video of it goes viral right now, Astra AI + our own creators). Conversion decides, views still count.
3. Tie-breakers: viral videos in the last 7 days, then in the last 30 days.

scores() below (smoothed share of viral / good videos, x our own creators' factor) is still computed for the weekly
report: our creators (own.py) move a format by how it does for US compared with their usual views.
"""
import re
import time

from .markets import PRIMARY, fkey


def scores(history, formats, cfg, m=PRIMARY, local=(), own_stats=None):
    r = cfg['ranking']
    viral, good = cfg['thresholds']['viral_views'], cfg['thresholds'].get('good_views', 20_000)
    own_stats = own_stats or {}
    k_own = r.get('own_prior_weight', 8)
    fk = fkey(m)
    local = set(local)
    out = {}
    for f in formats:
        if f.get('status') != 'active':
            continue
        n = hits = hits20 = 0.0
        for v in history.values():
            if v.get(fk) != f['id']:
                continue
            w = r.get('local_weight', 1) if v['handle'] in local else 1
            n += w
            hits += w * (v['views'] >= viral)
            hits20 += w * (v['views'] >= good)
        k = r['prior_weight']
        p100 = (hits + r['prior_hit_rate'] * k) / (n + k)
        p20 = (hits20 + r['prior_20k_rate'] * k) / (n + k)
        js_score = p100 + r['weight_20k'] * p20
        o = own_stats.get(f['id'], {})
        factor = 2 ** (o.get('lift_sum', 0.0) / (o.get('n', 0) + k_own))
        out[f['id']] = {'score': js_score * factor, 'js_score': js_score, 'own_factor': factor, 'videos': n,
                        'hits_100k': hits, 'hits_20k': hits20, 'own_videos': o.get('n', 0),
                        'own_hits_100k': o.get('hits_100k', 0), 'own_lift': o.get('lift', 0.0)}
    proven = sorted((v['score'] for v in out.values() if v['videos'] + v['own_videos'] >= 5), reverse=True)
    if len(proven) >= 3:
        cap = proven[2] - 1e-6
        for v in out.values():
            if v['videos'] + v['own_videos'] < 5:
                v['score'] = min(v['score'], cap)
    return out


def recent_viral(history, formats, cfg, m=PRIMARY):
    from . import hot
    return hot.counts(history, {}, formats, cfg['thresholds']['viral_views'], m)


def form(history, formats, cfg, own_stats=None, now=None):
    """Current form of EVERY format (list and archive): how likely one video of it does well right now. 1.0 = an
    average format at the moment.

    Astra AI part: share of its viral (80%) and good (20%) videos compared with all formats, where recent
    weeks count most (a video's weight halves every half_life_days). Few videos -> pulled towards 1.0, so a format
    with 6 tries is not judged like one with 30. Our part: x the factor from our own creators (see scores)."""
    lc = cfg.get('lineup', {})
    hl = lc.get('half_life_days', 21)
    k = cfg['ranking']['prior_weight'] * 0.5
    k_own = cfg['ranking'].get('own_prior_weight', 8)
    now = now or time.time()
    weight = lambda v: 0.5 ** ((now - v['created']) / 86400 / hl)
    viral, good = cfg['thresholds']['viral_views'], cfg['thresholds'].get('good_views', 20_000)
    tagged = [v for v in history.values() if v.get('format')]
    total = sum(weight(v) for v in tagged) or 1.0
    base = max(sum(weight(v) for v in tagged if v['views'] >= viral) / total, 1e-3)
    base20 = max(sum(weight(v) for v in tagged if v['views'] >= good) / total, 1e-3)
    per = {}
    for v in tagged:
        per.setdefault(v['format'], []).append(v)
    out = {}
    for f in formats:
        vs = per.get(f['id'], [])
        n = sum(weight(v) for v in vs)
        p100 = (sum(weight(v) for v in vs if v['views'] >= viral) + base * k) / (n + k)
        p20 = (sum(weight(v) for v in vs if v['views'] >= good) + base20 * k) / (n + k)
        js = 0.8 * p100 / base + 0.2 * p20 / base20
        o = (own_stats or {}).get(f['id'], {})
        factor = 2 ** (o.get('lift_sum', 0.0) / (o.get('n', 0) + k_own))
        out[f['id']] = {'form': js * factor, 'js_form': js, 'own_factor': factor, 'tries': n, 'all_videos': len(vs),
                        'own_videos': o.get('n', 0), 'own_lift': o.get('lift', 0.0)}
    return out


def own_stats(formats, cfg=None):
    from . import own, state
    return own.stats(state.load('own.json', {}), formats, time.time(),
                     viral_views=(cfg or {}).get('thresholds', {}).get('viral_views', 100_000))


def pin_sources(history, formats):
    """A format's own source video always counts for it (an unassigned one is assigned; never taken from another
    format). Without this a viral original that a later check left without a format would not count in the ranking."""
    for f in formats:
        m = re.search(r'/video/(\d+)', f.get('source_video') or '')
        v = history.get(m.group(1)) if m else None
        if v is not None and not v.get('format'):
            v['format'], v['judged'] = f['id'], True


def viral_30d(history, formats, cfg, now=None):
    """Viral videos (thresholds.viral_views+) of each format posted in the last 30 days - the tie-breaker when two
    formats have the same number of viral videos this week (user's rule, 11 Oct 2026)."""
    now = now or time.time()
    out = {}
    for v in history.values():
        if v.get('format') and v.get('views', 0) >= cfg['thresholds']['viral_views'] and now - v.get('created', 0) <= 30 * 86400:
            out[v['format']] = out.get(v['format'], 0) + 1
    return out


def order(history, formats, cfg, m=PRIMARY, local=()):
    from . import conversion, hot
    pin_sources(history, formats)
    o = own_stats(formats, cfg)
    s = scores(history, formats, cfg, m, local, o)
    fo = form(history, formats, cfg, o)
    conv, _ = conversion.board(history, formats, cfg, reach=fo)
    recent = recent_viral(history, formats, cfg, m)
    month = viral_30d(history, formats, cfg)
    hot_min = conversion.conf(cfg)['hot_min_conv']
    for fid in s:
        s[fid]['viral_30d'] = month.get(fid, 0)
        s[fid]['recent_viral'] = recent.get(fid, 0)
        s[fid]['recent_own'] = o.get(fid, {}).get('recent_viral', 0)
        s[fid]['form'] = fo[fid]['form']
        s[fid].update({k: conv[fid][k] for k in ('rate', 'conv', 'score', 'raw_rate')})
        s[fid]['saved_videos'] = conv[fid]['videos']
        s[fid]['hot'] = s[fid]['recent_viral'] >= hot.MIN_VIRAL and conv[fid]['conv'] >= hot_min
    return sorted(s, key=lambda fid: (-s[fid]['hot'], -s[fid]['score'],
                                      -(s[fid]['recent_viral'] + s[fid]['recent_own']), -s[fid]['viral_30d'])), s
