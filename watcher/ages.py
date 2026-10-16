"""🎓 "Fit it to your age" box under a script (user's request, 16 Oct 2026).

Many scripts are tied to one school level ("4th year of uni", "matura", "8th grade"). Our creators are of different
ages, so under such a script the page shows, per other level (primary school / high school / university), the few
words to swap - short, just the main point (user's rule: never whole sentences again). Scripts that do not depend on the school level
get no box. The script itself never changes (approved scripts stay locked); the box is a gray callout after the
script's last line (after the comment CTA).
"""
import json
import re

from . import llm, notion
from .brand import says_source
from .markets import TEXT, avoid_found, has_cta

LEVELS = ('osnovna', 'srednja', 'faks')
MARK = '🎓'
SYSTEM = 'You adapt TikTok creator scripts to the creator\'s school level. Reply with JSON only.'


CUE_RE = re.compile(r'\((?:🎥|📎)[^)]*\)\s*')  # recording / material cues: the creator sees them in the script above


def _norm(t):
    return re.sub(r'\s+', ' ', CUE_RE.sub('', t or '').strip())


def variants(lines, lang, model='opus'):
    """The few words to swap per school level, short (user's rule, 16 Oct 2026: just the main point, a few
    sentences - never whole lines again): [{'level': 'osnovna', 'swaps': [{'from': '…', 'to': '…'}]}] ([] = the script
    fits every level). 'from' is a short phrase exactly as it is in the script; at most 3 swaps per level."""
    T = TEXT[lang]
    numbered = '\n'.join(f'{i}. {t}' for i, t in enumerate(lines, 1))
    prompt = f"""Script of a TikTok video for creators to record ({T['lang_name']}, the page language):
{numbered}

Our creators are of different ages: primary school (upper grades), high school, or university. Some words in the
script only fit ONE school level (e.g. "4th year of uni", "faks", "matura", "8th grade", "professor" vs "teacher",
"exam period", "lecture" vs "class", a specific faculty or school, a grade average that only exists at one level).
For each OTHER level, list ONLY the few words a creator at that level must swap so the script fits them - the main
point, not whole sentences: each swap is a short phrase copied exactly from the script (2-8 words) and its
replacement (as short). At most 3 swaps per level; same meaning, joke and tone. Use real names of that country's
school system ({'Slovenia: osnovna šola, srednja šola/gimnazija, splošna matura, faks/fakulteta, profesor' if lang == 'sl' else 'Serbia/Croatia/Bosnia: osnovna škola, srednja škola/gimnazija, matura, faks/fakultet, profesor'}).
Rules: write in {T['lang_name']} ({T.get('style') or 'as spoken by young creators'}); never name any app except Memo AI;
never touch "Memo AI" or the comment line at the end. Leave out a level whose wording already fits (e.g. the script's
own level). If nothing depends on the school level, return empty lists.

Return JSON {{"osnovna": [{{"from": "<phrase from the script>", "to": "<primary-school wording>"}}], "srednja": [...],
"faks": [...]}}"""
    r = llm.chat_json(model, SYSTEM, prompt, timeout=900)
    script = _norm(' '.join(l for l in lines if not has_cta(l))).lower()
    out = []
    for lv in LEVELS:
        swaps, seen = [], set()
        for x in (r.get(lv) or [])[:3]:
            try:
                a, b = _norm(x.get('from')), _norm(x.get('to'))
            except AttributeError:
                continue
            if not a or not b or a.lower() == b.lower() or len(a) > 90 or len(b) > 90 or a.lower() not in script or a in seen:
                continue
            seen.add(a)
            swaps.append({'from': a, 'to': b})
        if swaps:
            out.append({'level': lv, 'swaps': swaps})
    return out


def problems(found, lang):
    """Reasons not to publish a box (same checks as the scripts: no other app, page language)."""
    T = TEXT[lang]
    text = ' '.join(w['to'] for x in found for w in x['swaps'])
    out = []
    if says_source(text):
        out.append('names the other app')
    if re.search(f"[{T['foreign']}]", text.lower()):
        out.append(f"non-{T['lang_name']} characters")
    bad = avoid_found(lang, text)
    if bad:
        out.append(f"{T['avoid_reason']}: {', '.join(bad[:5])}")
    return out


def box(found, lang):
    """The gray 🎓 callout: heading, one intro line, then one short line per school level with its swaps."""
    T = TEXT[lang]
    names = T['age_levels']
    rich = [notion.rt(T['age_h'], bold=True), notion.rt('\n' + T['age_intro'])]
    for x in found:
        rich.append(notion.rt(f"\n→ {names[x['level']]}: ", bold=True))
        rich.append(notion.rt('; '.join(f"»{w['from']}« → »{w['to']}«" for w in x['swaps']) + '.'))
    return notion.block('callout', rich, icon={'type': 'emoji', 'emoji': MARK}, color='gray_background')


def has_box(blocks):
    return any(b['type'] == 'callout' and ((b['callout'].get('icon') or {}).get('emoji')) == MARK for b in blocks)


def add_to_page(pid, lang, model='opus', script_blocks=None, plain=None, redo=False):
    """Adds the box to one page. Returns 'had' | 'none' (script fits every level) | 'added' | 'held: <why>'.
    redo: an existing box is replaced."""
    from . import reword
    blocks = notion.children(pid)
    if has_box(blocks) and not redo:
        return 'had'
    old = [b for b in blocks if b['type'] == 'callout' and ((b['callout'].get('icon') or {}).get('emoji')) == MARK]
    script = (script_blocks or reword.script_blocks)(pid)
    plain = plain or reword._plain
    lines = [_norm(plain(b)) for b in script if _norm(plain(b))]
    silent = lines and lines[0] == TEXT[lang]['silent_label']
    if silent:
        lines = lines[1:]
    if not lines:
        return 'held: no script found'
    found = variants(lines, lang, model)
    if not found:
        return 'none'
    why = problems(found, lang)
    if why:
        return 'held: ' + '; '.join(why)
    notion.api('PATCH', f'/blocks/{pid}/children', {'children': [box(found, lang)], 'after': script[-1]['id']})
    for b in old:  # the new box is in: the old one goes (never before - a page is never left without one)
        notion.api('DELETE', f"/blocks/{b['id']}")
    return 'added'


def dump(found):
    return json.dumps(found, ensure_ascii=False)
