"""🎓 "Fit it to your age" box under a script (user's request, 16 Oct 2026).

Many scripts are tied to one school level ("4th year of uni", "matura", "8th grade"). Our creators are of different
ages, so under such a script the page shows the same lines rewritten for the other levels (primary school / high
school / university) - the creator says the version that fits them. Scripts that do not depend on the school level
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
    """[{'line', 'versions': {level: text}}] for the script lines that depend on the school level ([] = none)."""
    T = TEXT[lang]
    numbered = '\n'.join(f'{i}. {t}' for i, t in enumerate(lines, 1))
    prompt = f"""Script of a TikTok video for creators to record ({T['lang_name']}, the page language):
{numbered}

Our creators are of different ages: primary school (upper grades), high school, or university. Find the lines whose
words only fit ONE school level (e.g. "4th year of uni", "faks", "matura", "8th grade", "professor" vs "teacher",
"exam period", "colloquium", "class teacher", a specific faculty or school). For each such line write how a creator at
each OTHER level says the same thing, keeping the same meaning, joke, length and tone - only the school-level details
change (year, school type, exam names, teacher/professor). Use real names of that country's school system
({'Slovenia: osnovna šola, srednja šola/gimnazija, splošna matura, faks/fakulteta, profesor' if lang == 'sl' else 'Serbia/Croatia/Bosnia: osnovna škola, srednja škola/gimnazija, matura, faks/fakultet, profesor'}).
Rules: write in {T['lang_name']} ({T.get('style') or 'as spoken by young creators'}); never name any app except Memo AI;
keep any "Memo AI" mention as it is; never change the comment line at the end; leave out lines that already fit every
level. If no line depends on the school level, return an empty list.

Return JSON {{"lines": [{{"n": <line number>, "osnovna": "<primary-school version or empty if the original already is
primary school or it makes no sense>", "srednja": "<high-school version or empty>", "faks": "<university version or
empty>"}}]}}"""
    r = llm.chat_json(model, SYSTEM, prompt, timeout=900)
    out = []
    for x in r.get('lines', []):
        try:
            line = lines[int(x['n']) - 1]
        except (KeyError, ValueError, IndexError, TypeError):
            continue
        if has_cta(line):
            continue
        vs = {lv: _norm(x.get(lv)) for lv in LEVELS if _norm(x.get(lv)) and _norm(x.get(lv)) != _norm(line)}
        if vs:
            out.append({'line': line, 'versions': vs})
    return out


def problems(found, lang):
    """Reasons not to publish a box (same checks as the scripts: no other app, page language)."""
    T = TEXT[lang]
    text = ' '.join(v for x in found for v in x['versions'].values())
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
    """The gray 🎓 callout: heading line, then per line the original and its versions."""
    T = TEXT[lang]
    names = T['age_levels']
    rich = [notion.rt(T['age_h'], bold=True), notion.rt('\n' + T['age_intro'])]
    for x in found:
        rich.append(notion.rt('\n\n„' + _norm(x['line'])[:1900] + '“', bold=False))
        for lv in LEVELS:
            if lv in x['versions']:
                rich += [notion.rt(f'\n→ {names[lv]}: ', bold=True), notion.rt(x['versions'][lv])]
    return notion.block('callout', rich[:95], icon={'type': 'emoji', 'emoji': MARK}, color='gray_background')


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
