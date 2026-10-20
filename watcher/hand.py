"""Formats written by hand with the user (registry/hand_scripts.json): no example video, our own script per page
language. Their pages sit in each market's list (after the ranked formats; on a market whose automation is stopped
they are the whole list). Pages: state/hand.json {market: {key: page_id}}. Built by mode=hand-scripts."""
import json
import os

from . import ages, notion, state
from .brand import DEMO_LABEL
from .markets import TEXT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, 'registry', 'hand_scripts.json')
LOGO = os.path.join(ROOT, 'registry', 'materials', '_logo', 'memo_ai_lockup_hq.png')
DEMO = '[DEMO]'

# the note at the top of the page (where built pages have the inspiration video)
NOTE = {
    'sl': ('✍️ Ta format smo napisali sami – nima videa za navdih. Posnemi se kot talking head (govoriš direktno v '
           'kamero) po spodnjem scenariju. Pri oznaki »🎥 Tukaj predvajaj Memo AI demo« predvajaj demo posnetek iz '
           'gradiva in ga posnemi, medtem ko govoriš naprej.'),
    'sh': ('✍️ Ovaj format smo napisali sami – nema videa za inspiraciju. Snimi se kao talking head (pričaš direktno u '
           'kameru) po scenariju ispod. Kod oznake »🎥 Ovdje pusti Memo AI demo« pusti demo snimak iz materijala i '
           'snimaj ga dok pričaš dalje.'),
}


def formats():
    with open(REGISTRY) as f:
        return json.load(f)['formats']


def pages():
    return state.load('hand.json', {})


def tail(market):
    """The hand-written pages of one market, in list order (only those already built)."""
    built = pages().get(market, {})
    return [built[f['key']] for f in formats() if built.get(f['key'])]


def demo_links(lang):
    """The note-taker demo recordings (config demo_videos_notetaker), else the market's usual demo recordings."""
    with open(os.path.join(ROOT, 'config.json')) as f:
        cfg = json.load(f)
    own = (cfg.get('demo_videos_notetaker') or {}).get(lang) or {}
    if not own.get('folder'):
        raise SystemExit(f'hand-scripts: config demo_videos_notetaker.{lang} has no Drive links yet')
    return own


def _record_rule(lang, videos):
    T = TEXT[lang]
    head, tail_ = T['record_rule'].split('{devices}')
    out = [notion.rt(' – ' + head)]
    for n, k in enumerate(('mac', 'windows', 'iphone', 'android')):
        if n:
            out.append(notion.rt(' · '))
        out.append(notion.rt(T['device_names'][k], link=videos.get(k) or videos.get('folder')))
    return out + [notion.rt(tail_)]


def page_blocks(fmt, lang, lab_url=None, logo_upload_id=None):
    """Same sections as a built format page (notion.page_blocks), with a note instead of the inspiration video."""
    T, spec, videos = TEXT[lang], fmt[lang], demo_links(lang)
    folder = videos.get('folder')
    blocks = [notion.block('callout', notion.md(NOTE[lang]), icon={'type': 'emoji', 'emoji': '⚠️'}, color='gray_background')]

    blocks.append(notion.block('heading_2', [notion.rt('📲'), notion.rt(T['title_h'], bold=True)]))
    blocks.append(notion.para([notion.rt(spec['title'], bold=True)]))
    blocks.append(notion.block('bulleted_list_item', [notion.rt(T['sub_voice'])]))
    blocks.append(notion.divider())

    blocks.append(notion.block('heading_2', [notion.rt(T['script_h'])]))
    for text in spec['script']:
        if DEMO in text:
            before, after = text.split(DEMO, 1)
            rich = ([notion.rt(before)] if before else []) + [
                notion.rt('('), notion.rt(f"🎥 {T['demo_start']}", link=folder), notion.rt(') '), notion.rt(after.lstrip())]
        else:
            rich = [notion.rt(text)]
        blocks.append(notion.para(rich))
    blocks.append(notion.para([notion.rt(T['cta'].format(word=spec['cta_word']))]))
    if spec.get('age_tip'):  # the 🎓 tip for creators at another school level, as on the built pages (ages.py)
        blocks.append(ages.box([{'tip': spec['age_tip']}], lang))
    blocks.append(notion.divider())

    blocks.append(notion.block('heading_2', [notion.rt(T['hook_h'])]))
    blocks.append(notion.para([notion.rt(spec['hook'])]))
    if lab_url:
        blocks.append(notion.para([notion.rt(T['hook_alt']), notion.rt('Visual Hook Lab', link=lab_url), notion.rt('.')]))
    blocks.append(notion.divider())

    blocks.append(notion.block('heading_2', [notion.rt('🔧'), notion.rt(T['res_h'], bold=True)]))
    res = [notion.rt(f'🎥 {DEMO_LABEL}', link=folder)] + _record_rule(lang, videos)
    if logo_upload_id:
        res.append(notion.rt('\n' + T['logo_line']))
    blocks.append(notion.block('callout', res, icon={'type': 'emoji', 'emoji': '💡'}, color='gray_background'))
    if logo_upload_id:
        blocks.append(notion.block('image', type='file_upload', file_upload={'id': logo_upload_id}))
    return blocks


def build(cfg, target=''):
    """Builds the missing hand-written pages of every market in cfg (enabled or not) under its list page.
    target 'key' = only that format; 'key!' (or '!' for all) = write the existing page(s) again from the registry."""
    redo = target.endswith('!')
    only = target.rstrip('!')
    built = pages()
    done = []
    for key, m in cfg['markets'].items():
        mp, lang = m, m['lang']
        lab = mp.get('visual_hook_lab')
        mine = built.setdefault(key, {})
        for f in formats():
            if only and f['key'] != only:
                continue
            if mine.get(f['key']) and not redo:
                continue
            logo = notion.upload_file(LOGO, 'image/png')
            blocks = page_blocks(f, lang, lab, logo)
            if mine.get(f['key']):
                notion.replace_content(mine[f['key']], blocks)
                notion.api('PATCH', f"/pages/{mine[f['key']]}", {'icon': {'type': 'emoji', 'emoji': '🎬'}})
            else:
                page = notion.create_page(mp['holder_page'], f[lang]['title'], '🎬', blocks)  # the built pages' icon
                mine[f['key']] = page['id']
            state.save('hand.json', built)
            done.append(f"{key}:{f['key']}")
            print(f"hand: {key} {f['key']} -> {mine[f['key']]}", flush=True)
    return done


def check(market, market_page, T):
    """verify: every hand-written format of the market has a page in the list's holder page, numbered in the list."""
    problems = []
    built = pages().get(market, {})
    holder = market_page['holder_page'].replace('-', '')
    for f in formats():
        pid = built.get(f['key'])
        if not pid:
            problems.append(f"{T['flag']} {f['key']}: hand-written format has no page")
            continue
        parent = (notion.api('GET', f'/pages/{pid}').get('parent') or {}).get('page_id', '').replace('-', '')
        if parent != holder:
            problems.append(f"{T['flag']} {f['key']}: hand-written page not in '{T['holder']}'")
    return problems
