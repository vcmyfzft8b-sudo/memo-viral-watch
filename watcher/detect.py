"""When is an Astra AI video "taking off" or "viral"? Thresholds live in config.json.

Taking off (early warning): within its first 6 / 24 / 48 hours a video has 5k / 20k / 50k views,
or (within 72h) at least 10x its creator's usual views and 5k+.
Viral (confirmed): 100k+ views within the watch window (7 days).
Converting: below the viral bar, but many viewers save it (conversion.converting, e.g. 30k+ views and 2%+ saved).
Saves (user's rule, 15 Oct 2026): a viral video that too few viewers save (conversion.min_save_rate) still alerts and
counts for its format, but never builds or brings back a format.
"""
import statistics


def creator_baseline(history, handle):
    """Median views of the creator's videos that are at least 7 days old (None if too few)."""
    views = [v['views'] for v in history.values() if v['handle'] == handle and v.get('mature')]
    return statistics.median(views) if len(views) >= 5 else None


def engagement(video):
    return (video['shares'] + video['saves']) / max(video['views'], 1)


def level(video, now, baseline, th, cfg=None):
    """Returns 'viral', 'converting', 'taking_off' or None (cfg: the whole config, for the conversion settings)."""
    from . import conversion
    age_h = (now - video['created']) / 3600
    views = video['views']
    if views >= th['viral_views']:
        return 'viral'
    if cfg is not None and conversion.converting(video, cfg):
        return 'converting'
    for hours, min_views in th['early']:
        if age_h <= hours and views >= min_views:
            return 'taking_off'
    if (baseline and age_h <= th['creator_multiple_max_age_hours']
            and views >= th['creator_multiple_min_views'] and views >= th['creator_multiple'] * baseline):
        return 'taking_off'
    return None
