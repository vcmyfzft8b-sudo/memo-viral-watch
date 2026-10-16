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
from .brand import CATEGORY, NO_DIRECTIONS, OURS, OURS_SITE, SOURCE, count_app, count_ours, count_source, says_source
from .markets import TEXT, conversion_rules, of, own, strip_cta

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
{CATEGORY}. It is built from the original video by our rules:
{conversion_rules(lang, own(fmt, lang))}
{('The original video on the page: ' + original[:2500]) if original else ''}
{('Note from the campaign team for this format (follow it): ' + fmt['brief']) if fmt.get('brief') else ''}

Correct the paragraphs so the script follows those rules. Natural {T['lang_name']} ({T['style']}). {SOURCE} (or
another study app) never appears; an app feature {OURS} does not have becomes the closest real one.
Rules:
- Keep every token ⟦n⟧...⟦/n⟧ exactly as it is (same number, same text inside) and in the same order and paragraph.
- Keep **bold** lines bold (they are on-screen texts). No backticks. Never mention {SOURCE}.
- Linked cue labels mark where the app/material is shown, they are not spoken words.
- {NO_DIRECTIONS}
- {T.get('localize') or 'Names of universities, schools, cities, shops etc. stay exactly as in the original.'}

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
        if align._words(strip_cta(spoken)) > 1.10 * align._words(base):
            return 'script exceeds 110% of the original word count', []
        want, have = count_app(base), count_ours(spoken)
        if have < 1:  # our rules: Memo AI is named where it comes in (cue labels do not count)
            return f'spoken brand count is {have}; Memo AI must be named where it comes in; cue labels do not count', []
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
    jobs = [(f, mk) for f in fmts if f.get('status') == 'active' for mk in of(mkts, f)
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
    """The visual hook section(s) as the reviewers see them: every text line under 🎬 (older pages: 👀), including the
    line offering the Visual Hook Lab - leaving that line out made the reviewer report it as missing, again and again.
    The example's TikTok link is never a direction."""
    out, inside = [], False
    for b in notion.children(page_id):
        if b['type'].startswith('heading'):
            inside = '🎬' in _plain(b) or '👀' in _plain(b)
            continue
        if b['type'] == 'divider':
            inside = False
            continue
        links = [((x.get('text') or {}).get('link') or {}).get('url') or '' for x in (b.get(b['type']) or {}).get('rich_text', []) or []]
        if inside and b['type'] in ('paragraph', 'bulleted_list_item') and _plain(b).strip() \
                and not any('tiktok.com' in u for u in links):
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
    from .align import approved_script
    fixed = (approved_script(fmt['id'], lang) or {}).get('hook')  # a visual hook the user approved is used as it is
    if fixed and len(lines) == 2 and _plain(lines[0]).strip() == fixed.strip() and 'Visual Hook Lab' in _plain(lines[1]):
        return 'ok', 'approved visual hook'
    if not fixed and (not issues and len(lines) == 2 and _plain(lines[0]).startswith(T['hook_start'].strip())
                      and 'Visual Hook Lab' in _plain(lines[1])):
        return 'ok', 'already in the short layout'
    if fixed:
        return _put_hook(page_id, head, section, fixed, lab, T)
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
    return _put_hook(page_id, head, section, hook, lab, T)


def _put_hook(page_id, head, section, hook, lab, T):
    """Replace the visual hook section with the hook sentence + the Visual Hook Lab line (old section backed up)."""
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


def fix_app_material_cues(page_id, link, lang=None):
    """'(📎 Memo AI · memoai.eu/creator – vidi materijale)' in a script is the app shown as a "material" - it becomes the
    normal app link cue '(Memo AI · memoai.eu/creator)'. Returns how many paragraphs changed."""
    from .brand import cue_label
    label = notion.cue_label_for(link, lang) if lang else cue_label(link)
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
                        {'type': 'text', 'text': {'content': label, 'link': {'url': link}}},
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
    the resources section for something that is not there (then the cue is removed)."""
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
                    clean = ''  # nothing in the resources to point to -> no cue (scripts have no stage directions)
                elif m.group(1).count('📎') > 1:
                    clean = TEXT[lang]['asset_cue'].format(name=name).strip()
                else:
                    continue
                t = re.sub(r' {2,}', ' ', t.replace(m.group(0), clean))
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


def ensure_app_link(page_id, link, lang):
    """A page without the app link cue gets it (verify: "no app link"): '(🎥 Predvajaj Memo AI demo) '
    in front of the first script line that names Memo AI (else the first line), and the same link with the recording
    rule at the top of the 🔧 materials box. Lines that already have it are left alone. Returns what was added."""
    label = notion.cue_label_for(link, lang)
    has_link = lambda b: any(((x.get('text') or {}).get('link') or {}).get('url') == link
                             for x in b[b['type']].get('rich_text', []))
    done = []
    script = script_blocks(page_id)
    if script and not any(has_link(b) for b in script):
        b = next((b for b in script if 'memo ai' in _plain(b).lower()), script[0])
        rich = [{k: v for k, v in x.items() if k in ('type', 'text', 'mention', 'annotations')}
                for x in b[b['type']].get('rich_text', [])]
        cue = [{'type': 'text', 'text': {'content': '('}},
               {'type': 'text', 'text': {'content': label, 'link': {'url': link}}},
               {'type': 'text', 'text': {'content': ') '}}]
        notion.api('PATCH', f"/blocks/{b['id']}", {b['type']: {'rich_text': cue + rich}})
        done.append('script')
    box = next((b for b in notion.children(page_id) if b['type'] == 'callout'
                and ((b['callout'].get('icon') or {}).get('emoji')) == '💡'), None)
    if box and not has_link(box):
        rich = [{k: v for k, v in x.items() if k in ('type', 'text', 'mention', 'annotations')}
                for x in box['callout'].get('rich_text', [])]
        head = [{'type': 'text', 'text': {'content': label, 'link': {'url': link}}}] + notion.record_rule_rich(lang, link)
        if rich:
            head.append({'type': 'text', 'text': {'content': '\n'}})
        notion.api('PATCH', f"/blocks/{box['id']}", {'callout': {'rich_text': head + rich}})
        done.append('materials')
    return done


def directions_left(page_id):
    """Bracketed stage directions / acting tips still in the script (not the app link cue, not a 📎 material cue)."""
    found = []
    for b in script_blocks(page_id):
        for x in b[b['type']].get('rich_text', []):
            if x.get('type') == 'text' and not ((x.get('text') or {}).get('link') or {}).get('url'):
                found += [m.group(0).strip() for m in notion.DIRECTION_RE.finditer(x.get('plain_text', ''))]
    return found


def strip_directions(page_id):
    """Removes bracketed stage directions / acting tips from the script (user's decision, 11 Oct 2026): only the app
    link cues and 📎 material cues stay in brackets. The old text is backed up first. Returns how many paragraphs changed."""
    changed = 0
    for b in script_blocks(page_id):
        rich, out, touched = b[b['type']].get('rich_text', []), [], False
        for x in rich:
            if x.get('type') == 'text' and not ((x.get('text') or {}).get('link') or {}).get('url'):
                t = x.get('plain_text', '')
                new = re.sub(r' {2,}', ' ', notion.DIRECTION_RE.sub('', t))
                if new != t:
                    touched = True
                if new:
                    out.append({'type': 'text', 'text': {'content': new}, 'annotations': x.get('annotations', {})})
            elif x.get('type') == 'text':
                out.append({'type': 'text', 'text': {'content': x['plain_text'], 'link': x['text']['link']},
                            'annotations': x.get('annotations', {})})
            else:
                out.append({k: v for k, v in x.items() if k in ('type', 'mention', 'equation', 'annotations')})
        if not touched:
            continue
        with state.LOCK:
            backup = state.load('script_backup.json', {})
            backup.setdefault('directions:' + b['id'], rich)
            state.save('script_backup.json', backup)
        if out and out[0]['type'] == 'text':
            out[0]['text']['content'] = out[0]['text']['content'].lstrip()
        if not ''.join(o.get('text', {}).get('content', '') for o in out).strip():
            notion.api('DELETE', f"/blocks/{b['id']}")  # the paragraph was only a direction
        else:
            notion.api('PATCH', f"/blocks/{b['id']}", {b['type']: {'rich_text': out}})
        changed += 1
    return changed
