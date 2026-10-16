"""🎓 "Fit it to your age" box under a script (user's request, 16 Oct 2026).

Many scripts are tied to one school level ("4th year of uni", "matura", "8th grade"). Our creators are of different
ages, so under such a script the page shows ONE short tip: what a creator at another level swaps (user's rule: "just a
tip" - one sentence). Scripts that do not depend on the school level
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
    """One short tip for creators at another school level (user's rule, 16 Oct 2026: "just a tip" - one sentence, never
    lists or whole lines): [{'tip': '…'}], or [] when the script fits every level."""
    T = TEXT[lang]
    numbered = '\n'.join(f'{i}. {t}' for i, t in enumerate(lines, 1))
    prompt = f"""Script of a TikTok video for creators to record ({T['lang_name']}, the page language):
{numbered}

Our creators are of different ages: primary school (upper grades), high school, or university. Does the script's
STORY depend on one school level (e.g. "4th year of uni", "8th grade", "matura", a grade average only one level has,
a specific faculty or school)? If yes, write ONE short tip (one sentence, at most 140 characters) telling a creator at
another level what to swap, quoting at most the one or two key words from the script, e.g. "Ako ne ideš na faks,
umjesto »prvu godinu studija« reci svoj razred i svoj prosjek." Ignore everyday words that fit everyone well enough
("predavanje"/"lecture" in the app pitch, "profesor", "test"). Use the country's school words
({'Slovenia: osnovna šola, srednja šola/gimnazija, matura, faks' if lang == 'sl' else 'Serbia/Croatia/Bosnia: osnovna škola, srednja škola/gimnazija, matura, faks'}).
Write in {T['lang_name']} ({T.get('style') or 'as spoken by young creators'}); never name any app.
If the story fits every level, return an empty tip.

Return JSON {{"tip": "<the one sentence, or empty>"}}"""
    r = llm.chat_json(model, SYSTEM, prompt, timeout=900)
    tip = _norm(r.get('tip'))
    if not tip or len(tip) > 220 or has_cta(tip):
        return []
    return [{'tip': tip}]


def problems(found, lang):
    """Reasons not to publish a box (same checks as the scripts: no other app, page language)."""
    T = TEXT[lang]
    text = ' '.join(x['tip'] for x in found)
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
    """The gray 🎓 callout: one line - 'Savjet za tvoj uzrast: <tip>'."""
    T = TEXT[lang]
    return notion.block('callout', [notion.rt(T['age_h'] + ' ', bold=True), notion.rt(found[0]['tip'])],
                        icon={'type': 'emoji', 'emoji': MARK}, color='gray_background')


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
