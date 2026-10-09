"""Read-only health check of everything in Notion (mode verify): compares the live pages with the state and prints
one line per problem. Nothing is changed.

Per market: the list (layout as on the Parakeet list, ▶️ entries = the live formats in ranking order, numbered 1., 2.,
…), every live format page (in the market's "all formats" folder, example video, script with app links, visual hook,
materials), every held page (still in the private staging area, invisible to creators) and the Visual Hook Lab.
"""
import re

from . import notion, rank, state
from .markets import TEXT


def _plain(b):
    return ''.join(x.get('plain_text', '') for x in (b.get(b['type']) or {}).get('rich_text', []) or [])


def _parent(page_id):
    return ((notion.api('GET', f'/pages/{page_id}').get('parent') or {}).get('page_id') or '').replace('-', '')


def _title(page_id):
    p = notion.api('GET', f'/pages/{page_id}')
    return ''.join(x['plain_text'] for x in next(v for v in p['properties'].values() if v['type'] == 'title')['title'])


def check_page(pid, T, links):
    """Problems of one format page in our layout."""
    blocks = notion.children(pid)
    text = ' '.join(_plain(b) for b in blocks)
    urls = [((x.get('text') or {}).get('link') or {}).get('url', '') for b in blocks
            for x in (b.get(b['type']) or {}).get('rich_text', []) or []]
    out = []
    if not any(b['type'] == 'video' for b in blocks):
        out.append('no example video')
    for need in (T['video_heading'], T['title_h'], T['script_h'].lstrip('💬'), T['hook_h'], T['res_h']):
        if need not in text:
            out.append(f'section missing: {need}')
    if not any('tiktok.com/@' in u for u in urls):
        out.append('no link to the original TikTok')
    if not any(u == links['memo'] for u in urls):
        out.append(f"no app link to {links['memo']}")
    if any('memoai.eu' in u and u != links['memo'] for u in urls):
        out.append('old app link left')
    if re.search(r'astra', ' '.join(_plain(b) for b in blocks if b['type'] != 'callout'), re.I):
        out.append('Astra mentioned outside the note')
    return out


def run(cfg, fmts, page_of):
    pages = state.load('notion.json', {})
    history = state.load('history.json', {})
    radar = (pages.get('radar_page') or '').replace('-', '')
    problems, ok = [], []
    ids, _ = rank.order(history, fmts, cfg)
    by_id = {f['id']: f for f in fmts}
    for key, m in cfg['markets'].items():
        T, mp = TEXT[m['lang']], pages['markets'][key]
        flag = T['flag']
        # the list
        blocks = notion.children(mp['list_page'])
        icons = [((b.get('callout') or {}).get('icon') or {}).get('emoji') for b in blocks]
        if '🔥' not in icons or '🚨' not in icons or not any(b['type'] == 'toggle' for b in blocks):
            problems.append(f'{flag} list layout incomplete (🔥 / 🚨 / 📁 toggle)')
        entries, _ = notion.list_entries(mp['list_page'])
        listed = [p.replace('-', '') for _, p in entries]
        want = [page_of(by_id[i], key).replace('-', '') for i in ids if page_of(by_id[i], key)]
        if listed != want:
            problems.append(f'{flag} list order/content differs: listed {len(listed)}, expected {len(want)}')
        else:
            ok.append(f'{flag} list: {len(listed)} formats in ranking order')
        for n, pid in enumerate(listed, 1):
            t = _title(pid)
            if not t.startswith(f'{n}. '):
                problems.append(f'{flag} list entry {n} not numbered: {t[:50]}')
        # the format pages
        holder = mp['holder_page'].replace('-', '')
        for f in fmts:
            pid = page_of(f, key)
            if not pid:
                if f.get('status') in ('active', 'pending'):
                    problems.append(f"{flag} {f['title']}: no page")
                continue
            where = _parent(pid)
            if f.get('status') == 'active' and where != holder:
                problems.append(f"{flag} {f['title']}: live but not in '{T['holder']}'")
            if f.get('status') == 'pending' and where == holder:
                problems.append(f"{flag} {f['title']}: held but visible in '{T['holder']}'")
            if f.get('status') == 'pending' and where != radar:
                problems.append(f"{flag} {f['title']}: held page not in the staging area")
            if f.get('status') == 'active':
                bad = check_page(pid, T, cfg['links'])
                problems += [f"{flag} {f['title']}: {x}" for x in bad]
                if not bad:
                    ok.append(f"{flag} {f['title']}: page complete")
        # the Visual Hook Lab
        lab = mp['visual_hook_lab'].rstrip('/').split('/')[-1].split('-')[-1]
        videos = sum(1 for b in _walk(lab) if b['type'] == 'video')
        (ok if videos >= 10 else problems).append(f'{flag} Visual Hook Lab: {videos} videos')
    print('\n'.join(['VERIFY OK:'] + ['  ' + x for x in ok] + ['VERIFY PROBLEMS:'] + ['  ' + x for x in problems or ['none']]))
    return problems


def _walk(block_id):
    for b in notion.children(block_id):
        yield b
        if b.get('has_children') and b['type'] not in ('child_page', 'child_database'):
            yield from _walk(b['id'])
