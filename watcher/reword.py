"""Correct the scripts on the existing format pages towards the Astra AI original (same beats, same order,
same length, same hook idea): the original transcribed / translated almost one to one, only the app swapped.

Only the script section of a page changes (from the 💬 heading to the next divider/heading). Every link cue in it
(Memo AI, recordings, ...) and every bold on-screen line stays where it is: the text is sent to Claude with
the links as numbered tokens, and a reworded paragraph is only written back if all tokens come back unchanged and
in the same order and the length stays within ±20%. The old text of every changed block is kept in
state/script_backup.json, so a page can be restored.
"""
import json
import re

from . import llm, notion, state
from .brand import CATEGORY, OURS, OURS_SITE, SOURCE, count_ours, count_source, says_source
from .markets import TEXT

TOKEN = re.compile(r'⟦(\d+)⟧(.*?)⟦/\1⟧', re.S)


def _plain(b):
    return ''.join(x.get('plain_text', '') for x in b[b['type']].get('rich_text', []))


def script_blocks(page_id):
    """The blocks of the page's script section (between the 💬 heading and the next divider/heading)."""
    blocks = notion.children(page_id)
    start = next((i for i, b in enumerate(blocks) if b['type'].startswith('heading') and
                  re.search(r'💬|SCENARIJ|SKRIPT|SCRIPT', _plain(b), re.I)), None)
    if start is None:
        return []
    out = []
    for b in blocks[start + 1:]:
        if b['type'] == 'divider' or b['type'].startswith('heading'):
            break
        if b['type'] in ('paragraph', 'bulleted_list_item', 'numbered_list_item', 'quote') and _plain(b).strip():
            out.append(b)
    return out


def encode(b):
    """Block text with links as ⟦n⟧label⟦/n⟧ tokens and bold as **...**; None if it has things we must not touch."""
    parts, links = [], []
    for x in b[b['type']].get('rich_text', []):
        if x['type'] != 'text':
            return None, None
        t = x['plain_text']
        link = ((x.get('text') or {}).get('link') or {}).get('url')
        if link:
            links.append((link, t, x.get('annotations', {})))
            parts.append(f'⟦{len(links)}⟧{t}⟦/{len(links)}⟧')
        elif x.get('annotations', {}).get('bold') and t.strip():
            parts.append(f'**{t}**')
        else:
            parts.append(t)
    return ''.join(parts), links


def decode(text, links):
    rich, pos = [], 0
    def plain(seg):
        for k, piece in enumerate(re.split(r'\*\*', seg)):
            if piece:
                rich.append({'type': 'text', 'text': {'content': piece}, 'annotations': {'bold': k % 2 == 1}})
    for m in TOKEN.finditer(text):
        plain(text[pos:m.start()])
        url, label, ann = links[int(m.group(1)) - 1]
        rich.append({'type': 'text', 'text': {'content': label, 'link': {'url': url}}, 'annotations': ann})
        pos = m.end()
    plain(text[pos:])
    return rich


def reword_page(fmt, page_id, lang, model, original='', feedback=''):
    from . import align
    if align.approved_script(fmt['id'], lang):
        return 'skipped', 'approved script is locked', []
    if not original:
        return 'skipped', 'source evidence required for sentence-aligned rewrite', []
    blocks = script_blocks(page_id)
    enc = [(b, *encode(b)) for b in blocks]
    enc = [(b, t, l) for b, t, l in enc if t is not None]
    if not enc:
        return 'skipped', 'no script section found', []
    T = TEXT[lang]
    numbered = '\n'.join(f'{i}: {t}' for i, (_, t, _) in enumerate(enc))
    prompt = f"""This is the {T['lang_name']} script of a UGC video format ("{fmt['title']}") for {OURS}, an
{CATEGORY}. It must be the original {SOURCE} video, transcribed and translated (if needed) almost one to one.
{('The original video on the page: ' + original[:2500]) if original else ''}

Make EVERY paragraph a faithful translation/transcription of the matching part of the original: the same sentences in
the same order, the same meaning, words, jokes, numbers, places and claims; nothing added, nothing left out, nothing
reworded. Natural {T['lang_name']} ({T['style']}). Only these differ from the original: {SOURCE} (or another study
app it promotes) becomes {OURS} and its website {OURS_SITE} - exactly where and as often as the original names it,
zero times if the original never names it -, and an app feature {OURS} does not have becomes the closest real one.
Rules:
- Keep every token ⟦n⟧...⟦/n⟧ exactly as it is (same number, same text inside) and in the same order and paragraph.
- Keep **bold** lines bold (they are on-screen texts). No backticks. Never mention {SOURCE}.
- Linked cue labels are filming directions, not spoken words.

{('A reviewer found these problems - fix them: ' + feedback) if feedback else ''}

Paragraphs:
{numbered}

Return JSON {{"paragraphs": ["<reworded paragraph 0>", "<reworded paragraph 1>", ...]}} with exactly {len(enc)} items."""
    why = ''
    for attempt in range(3):
        extra = f'\n\nYour previous attempt was rejected: {why}. Fix exactly that.' if why else ''
        r = llm.chat_json(model, 'You are a senior UGC script writer. Reply with JSON only.', prompt + extra, timeout=1200)
        why, changes = _validate(enc, r.get('paragraphs', []), original)
        if not why:
            return 'ok', '', changes
    return 'skipped', why, []


def _validate(enc, new, original=''):
    if len(new) != len(enc):
        return f'returned {len(new)} paragraphs instead of {len(enc)}', []
    changes = []
    for i, ((b, old, links), text) in enumerate(zip(enc, new)):
        if [m.group(1) for m in TOKEN.finditer(old)] != [m.group(1) for m in TOKEN.finditer(text)]:
            return f'paragraph {i}: the link tokens must stay exactly the same and in the same order', []
        if says_source(text):
            return f'paragraph {i}: {SOURCE} appeared', []
        if len(old) > 60 and not 0.75 <= len(text) / len(old) <= 1.25:
            return f'paragraph {i}: length changed too much ({len(text)} vs {len(old)} characters)', []
        changes.append((b, old, text, links))
    if original:
        from . import align
        base = align.source_script(original)
        rendered = [{'type': b['type'], b['type']: {'rich_text': decode(text, links)}} for b, _, text, links in changes]
        spoken = spoken_text(rendered)
        if align._words(spoken) > 1.10 * align._words(base):
            return 'script exceeds 110% of the original word count', []
        want, have = count_source(base), count_ours(spoken)
        if have != want:
            return f'spoken brand count is {have}; source requires {want}; cue labels do not count', []
    return '', changes


def apply(changes):
    with state.LOCK:  # backup first (so the original text is never lost), then write to Notion
        backup = state.load('script_backup.json', {})
        for b, old, text, links in changes:
            backup.setdefault(b['id'], b[b['type']]['rich_text'])
        state.save('script_backup.json', backup)
    for b, old, text, links in changes:
        notion.api('PATCH', f"/blocks/{b['id']}", {b['type']: {'rich_text': decode(text, links)}})


def run(fmts, mkts, cfg, page_of, originals=None, dry=False):
    """Returns [(format title, market, status, detail, changes)]."""
    import concurrent.futures as cf
    jobs = [(f, mk) for f in fmts if f.get('status') == 'active' for mk in mkts
            if page_of(f, mk['key']) and not (f.get('reworded') or {}).get(mk['key'])]

    def one(job):
        f, mk = job
        try:
            from . import localize
            pid = page_of(f, mk['key'])
            src = localize.current_source(pid)
            ref = localize.example_text(src.get('url') if src else None, page_id=pid) or (originals or {}).get(f['id'], '')
            status, why, changes = reword_page(f, pid, mk['lang'], cfg['models']['build'], ref)
            return f, mk, status, why, changes
        except Exception as e:
            return f, mk, 'error', str(e)[:150], []
    out = []
    with cf.ThreadPoolExecutor(3) as ex:
        for f, mk, status, why, changes in ex.map(one, jobs):
            if status == 'ok' and not dry:
                apply(changes)
                f.setdefault('reworded', {})[mk['key']] = True
            out.append((f['title'], mk['key'], status, why, changes))
    return out


def direction_blocks(page_id):
    """Blocks of the 🎬 filming-directions section (without the mandatory 🚨 line and the Visual Hook Lab link)."""
    blocks = notion.children(page_id)
    out, inside = [], False
    for b in blocks:  # 🎬 = directions (👀 = an older heading for them)
        if b['type'].startswith('heading'):
            inside = '🎬' in _plain(b) or '👀' in _plain(b)
            continue
        if b['type'] == 'divider':
            inside = False
            continue
        t = _plain(b)
        has_link = any(((x.get('text') or {}).get('link') or {}).get('url', '').startswith('http') and
                       OURS_SITE not in ((x.get('text') or {}).get('link') or {}).get('url', '')
                       for x in b.get(b['type'], {}).get('rich_text', []))
        if inside and b['type'] in ('paragraph', 'bulleted_list_item') and t.strip() and '🚨' not in t \
                and 'Visual Hook Lab' not in t and not has_link:  # the example's TikTok link is never a direction
            out.append(b)
    return out


def hook_section(page_id):
    """(heading block, [blocks of the 🎬 visual hook section up to the next divider/heading])."""
    blocks = notion.children(page_id)
    k = next((n for n, b in enumerate(blocks) if b['type'].startswith('heading') and ('🎬' in _plain(b) or '👀' in _plain(b))), None)
    if k is None:
        return None, []
    out = []
    for b in blocks[k + 1:]:
        if b['type'] == 'divider' or b['type'].startswith('heading'):
            break
        out.append(b)
    return blocks[k], out


def fix_directions(fmt, page_id, lang, model, issues=''):
    """The visual hook section is only: one sentence (two at most) telling the creator to copy the example video's
    visual hook, then one line offering the Visual Hook Lab instead (user's decision, 10 Oct 2026). Rewrites any older
    or longer section into that. Returns (status, why)."""
    import json as _json
    T = TEXT[lang]
    head, section = hook_section(page_id)
    if head is None:
        return 'skipped', 'no visual hook section'
    lab = next((((x.get('text') or {}).get('link') or {}).get('url') for b in section
                for x in (b.get(b['type']) or {}).get('rich_text', []) or []
                if 'Visual Hook Lab' in x.get('plain_text', '') and ((x.get('text') or {}).get('link') or {}).get('url')), None)
    if not lab:
        with open(__import__('os').path.join(__import__('os').path.dirname(__file__), '..', 'config.json')) as fh:
            cfg = _json.load(fh)
        lab = (state.load('notion.json', {}).get('markets', {}).get(next((k for k, m in cfg['markets'].items()
                                                                         if m['lang'] == lang), ''), {}) or {}).get('visual_hook_lab')
    lines = [b for b in section if _plain(b).strip()]
    if (not issues and len(lines) == 2 and _plain(lines[0]).startswith(T['hook_start'].strip())
            and 'Visual Hook Lab' in _plain(lines[1])):
        return 'ok', 'already in the short layout'
    old = '\n'.join(_plain(b) for b in lines)
    prompt = f"""This is the visual hook section ({T['lang_name']}) of a UGC creator page. The first line(s) describe
what the creator of the example video does in the first seconds of the video.
CURRENT SECTION:
{old[:3000]}
{('A reviewer found: ' + issues) if issues else ''}
Write the new section: ONE sentence (two at most) in {T['lang_name']} ({T['style']}) that starts exactly with
"{T['hook_start']}" and then says concretely what to copy from the example's opening (action, prop, where to look,
what is on screen). Nothing else - no filming tips, no app instructions, no scores, no "back to the camera".
Return JSON {{"hook": "<the sentence(s)>"}}"""
    r = llm.chat_json(model, 'You are a precise editor of creator instructions. Reply with JSON only.', prompt, timeout=600)
    hook = (r.get('hook') or '').strip()
    if not hook:
        return 'skipped', 'no hook sentence returned'
    if not hook.lower().startswith(T['hook_start'].strip().lower()[:20]):
        hook = T['hook_start'] + hook[0].lower() + hook[1:]
    with state.LOCK:  # old section kept, so a page can be restored
        backup = state.load('script_backup.json', {})
        backup.setdefault('hook:' + page_id, [b[b['type']].get('rich_text', []) for b in section if b.get(b['type'])])
        state.save('script_backup.json', backup)
    new = [notion.para([notion.rt(hook)])]
    new.append(notion.para([notion.rt(T['hook_alt'])] + ([notion.rt('Visual Hook Lab', link=lab)] if lab else
                                                          [notion.rt('Visual Hook Lab')]) + [notion.rt('.')]))
    notion.api('PATCH', f'/blocks/{page_id}/children', {'children': new, 'after': head['id']})
    for b in section:
        notion.api('DELETE', f"/blocks/{b['id']}")
    return 'ok', hook[:120]


def resources_text(page_id):
    """Plain text of the page's 🔧 resources section (what a '📎 … – see resources' cue may point to)."""
    out, inside = [], False
    for b in notion.children(page_id):
        if b['type'].startswith('heading'):
            inside = '🔧' in _plain(b)
            continue
        if inside and b['type'] != 'divider':
            out.append(_plain(b))
            if b.get('has_children'):  # e.g. a recording link sits inside the resources callout
                out += [_plain(c) for c in notion.children(b['id']) if c.get(c['type'], {}).get('rich_text') is not None]
    return ' '.join(out).lower()


def in_resources(name, resources):
    """True if the asset is really in the resources section (e.g. 'class group chat' -> 'group chat recording')."""
    words = [w for w in re.findall(r'\w+', (name or '').lower()) if len(w) >= 4]
    return any(w in resources for w in words)


def fix_app_material_cues(page_id, link):
    """'(📎 Memo AI · memoai.eu/creator – vidi materijale)' in a script is the app shown as a "material" - it becomes the
    normal app link cue '(Memo AI · memoai.eu/creator)'. Returns how many paragraphs changed."""
    from .brand import CUE_LABEL
    pat = re.compile(r'\((?:📎\s*)+Memo AI[^()]*\)\s*')
    fixed = 0
    for b in script_blocks(page_id):
        rich, out, changed = b[b['type']].get('rich_text', []), [], False
        for x in rich:
            if x.get('type') != 'text' or not pat.search(x.get('plain_text', '')):
                out.append({k: v for k, v in x.items() if k in ('type', 'text', 'mention', 'annotations')})
                continue
            changed = True
            t, pos = x['plain_text'], 0
            for m in pat.finditer(t):
                if t[pos:m.start()]:
                    out.append({'type': 'text', 'text': {'content': t[pos:m.start()]}, 'annotations': x.get('annotations', {})})
                out += [{'type': 'text', 'text': {'content': '('}},
                        {'type': 'text', 'text': {'content': CUE_LABEL, 'link': {'url': link}}},
                        {'type': 'text', 'text': {'content': ') '}}]
                pos = m.end()
            if t[pos:]:
                out.append({'type': 'text', 'text': {'content': t[pos:]}, 'annotations': x.get('annotations', {})})
        if changed:
            notion.api('PATCH', f"/blocks/{b['id']}", {b['type']: {'rich_text': out}})
            fixed += 1
    return fixed


def fix_asset_cues(page_id):
    """Repairs script cues: decorated more than once ('📎 📎 📎 … – vidi materijale – vidi materijale'), or pointing to
    the resources section for something that is not there (then it is a plain stage direction '(eDnevnik)')."""
    suffixes = {l: TEXT[l]['asset_cue'].split('{name}')[1].strip(' )') for l in TEXT}
    resources = None
    fixed = 0
    for b in script_blocks(page_id):
        rich = b[b['type']].get('rich_text', [])
        changed = False
        for x in rich:
            if not x.get('text'):
                continue
            t = x['text'].get('content', '')
            for m in re.finditer(r'\((📎[^()]*)\)', t):
                lang = next((l for l, suf in suffixes.items() if suf in m.group(1)), None)
                if not lang:
                    continue
                name = notion.asset_label(m.group(1))
                if resources is None:
                    resources = resources_text(page_id)
                if not in_resources(name, resources):
                    clean = f'({name})'
                elif m.group(1).count('📎') > 1:
                    clean = TEXT[lang]['asset_cue'].format(name=name).strip()
                else:
                    continue
                t = t.replace(m.group(0), clean)
                changed = True
            x['text']['content'] = t
        if changed:
            notion.api('PATCH', f"/blocks/{b['id']}", {b['type']: {'rich_text': [
                {'type': 'text', 'text': x['text'], 'annotations': x.get('annotations', {})} for x in rich if x.get('text')]}})
            fixed += 1
    return fixed


def spoken_text(blocks):
    """What is actually said/shown as script text: without link labels, (cue) brackets and the silent label."""
    out = []
    for b in blocks:
        parts = []
        for x in b[b['type']].get('rich_text', []):
            if ((x.get('text') or {}).get('link') or {}).get('url'):
                continue  # cue link label
            parts.append(x.get('plain_text', x.get('text', {}).get('content', '')))
        t = re.sub(r'\([^)]*\)\s*', '', ''.join(parts))
        if any(t.strip().startswith(TEXT[l]['silent_label']) for l in TEXT):
            continue
        out.append(t)
    return '\n'.join(out)
