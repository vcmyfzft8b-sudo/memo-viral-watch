"""One demo cue per script, right after the app is named (user's rule, 16 Oct 2026).

Creators play the Memo AI demo recording from the 🎥 mark to its end and talk over it, so a script has exactly one
demo cue: right after the creator says "Memo AI" (or "this app") in the paragraph where the app comes in - after the
end of that sentence when it is short, else right after the name (when the cue is on an on-screen text line, in the
next paragraph, where the creator says it). Later demo cues are dropped. A format with its own
app page (the oral quiz) keeps its cues: this is only for the demo recordings.

`fix_spec` does it on a script spec (registry/approved_scripts.json, page rendering); `fix_page` on a live page;
`restore` changes a live paragraph's wording back (mode=repitch, registry/demo_pitch.json).
"""
import re

from . import notion
from .brand import CUE, is_demo_link
from .markets import TEXT

_THIS = r'\b(?:ta|tale|tole|ovu|ova|ovo|ovom|tu|to)\s+(?:app|aplikacij[aeiou]\w*)\b'
APP_RE = re.compile(rf'(?:{_THIS},?\s*)?Memo\s?AI|{_THIS}', re.I)  # "ovu aplikaciju, Memo AI" counts as one name
NEAR = 60  # a sentence that ends this soon after the name: the cue goes after its end
END_RE = re.compile(r'[.:!?]+[»«“”"\')]*')
SOFT_RE = re.compile(r',|\s[–-]\s')  # no sentence end near: after a comma or before a dash close to the name
SOFT_NEAR = 25


def anchor(text, screen_label=''):
    """Where in this text the demo starts: just after the app's name (see the module doc), or None."""
    if screen_label and text.lstrip().startswith(screen_label):
        return None  # an on-screen text line is not something the creator says
    m = next((m for m in APP_RE.finditer(text or '')
              if not (text[:m.start()].strip() == '' and text[m.end():m.end() + 1] == ':')), None)  # "Memo AI:" = a speaker
    if not m:
        return None
    end = END_RE.search(text, m.end())
    if end and end.start() - m.end() <= NEAR:
        return end.end()
    soft = SOFT_RE.search(text, m.end())
    if soft and soft.start() - m.end() <= SOFT_NEAR:
        return soft.end() if soft.group() == ',' else soft.start()
    return m.end()


def fix_spec(script, lang):
    """The script segments with one demo cue, placed after the app's name. Segments are split where needed;
    nothing else changes."""
    first = next((i for i, s in enumerate(script) if s.get('cue') == CUE), None)
    if first is None:
        return script
    out = [dict(s, cue=None) if s.get('cue') == CUE and i != first else dict(s) for i, s in enumerate(script)]
    start = first
    while start > 0 and not out[start].get('new_paragraph'):
        start -= 1
    end = first + 1
    while end < len(out) and not out[end].get('new_paragraph'):
        end += 1
    label = TEXT[lang].get('screen_label', '')
    nxt = end + 1
    while nxt < len(out) and not out[nxt].get('new_paragraph'):
        nxt += 1
    spans = [(start, end)]
    if (out[start].get('text') or '').lstrip().startswith(label or '\0') and end < len(out):
        spans.append((end, nxt))  # the cue is on an on-screen text line: the creator says the name in the next paragraph
    for lo, hi in spans:
        for i in range(lo, hi):
            pos = anchor(out[i].get('text') or '', label)
            if pos is None:
                continue
            text = out[i]['text']
            head, tail = text[:pos].rstrip(), text[pos:].strip()
            if i == first and not head:
                return out  # the cue is already right before the name
            if not tail:  # the name ends the segment: the cue goes on the next one (in the next paragraph too)
                if i + 1 < len(out):
                    out[first] = dict(out[first], cue=None)
                    out[i + 1] = dict(out[i + 1], cue=CUE)
                return out
            out[first] = dict(out[first], cue=None)
            return out[:i] + [dict(out[i], text=head), dict(out[i], text=tail, cue=CUE, new_paragraph=False, asset_name='')] + out[i + 1:]
    return out


def _cue(x):
    url = ((x.get('text') or {}).get('link') or {}).get('url') or ''
    return x.get('type') == 'text' and is_demo_link(url) and x.get('plain_text', '').startswith('🎥')


def _text(content, x=None):
    return {'type': 'text', 'text': {'content': content, 'link': ((x or {}).get('text') or {}).get('link')},
            'annotations': (x or {}).get('annotations', {})}


def _keep(x):
    if x.get('type') == 'text':
        return _text(x['plain_text'], x)
    return {k: v for k, v in x.items() if k in ('type', 'mention', 'annotations')}


def _insert(items, pos, cue):
    """items with the cue inserted at character position pos of their joined text (a text item is split there)."""
    at = 0
    for n, x in enumerate(items):
        t = x['text']['content'] if x.get('type') == 'text' else ''
        if at + len(t) >= pos and x.get('type') == 'text' and not (x['text'].get('link')):
            k = pos - at
            head, tail = t[:k], t[k:]
            left = [_text(head.rstrip() + ' ', x)] if head.strip() else []
            right = [_text(tail.lstrip(), x)] if tail.strip() else []
            return items[:n] + left + cue + right + items[n + 1:]
        at += len(t)
    return items + cue


def _drop_cues(items, idx):
    """items (send format) without the demo cues at positions idx and their brackets."""
    items = list(items)
    for n in sorted(idx, reverse=True):
        items[n] = None
        if n > 0 and items[n - 1] and items[n - 1].get('type') == 'text':
            items[n - 1]['text']['content'] = re.sub(r'\s*\($', ' ', items[n - 1]['text']['content'])
        if n + 1 < len(items) and items[n + 1] and items[n + 1].get('type') == 'text':
            items[n + 1]['text']['content'] = re.sub(r'^\)\s*', '', items[n + 1]['text']['content'])
    items = [x for x in items if x and not (x.get('type') == 'text' and x['text']['content'].strip() == '')]
    if items and items[0].get('type') == 'text':
        items[0]['text']['content'] = items[0]['text']['content'].lstrip()
    return items


def reads(text, want):
    """True when a paragraph's text, without its 🎥 cues and spaces aside, is `want`."""
    norm = lambda t: re.sub(r'\s+', ' ', t).strip()
    return norm(re.sub(r'\(🎥[^)]*\)', ' ', text)) == norm(want)


def restore(rich_text, now, old):
    """A live script paragraph's rich_text with its wording changed back: `now` (how it reads without the 🎥 cue,
    spaces ignored) -> `old`. Links and mentions stay; a 🎥 demo cue goes to the start (fix_page places it).
    None when the paragraph does not read `now` or the change would touch a link."""
    norm = lambda t: re.sub(r'\s+', ' ', t).strip()
    cue = next((x for x in rich_text if _cue(x)), None)
    items, merged = _drop_cues([_keep(x) for x in rich_text], [n for n, x in enumerate(rich_text) if _cue(x)]), []
    for x in items:  # plain text pieces next to each other become one
        prev = merged[-1] if merged else None
        if (prev and prev.get('type') == x.get('type') == 'text' and not prev['text'].get('link')
                and not x['text'].get('link') and prev.get('annotations') == x.get('annotations')):
            prev['text']['content'] += x['text']['content']
        else:
            merged.append(x)
    texts = [x['text']['content'] if x.get('type') == 'text' else '' for x in merged]
    text = ''.join(texts)
    if norm(text) != norm(now):
        return None
    p = 0
    while p < min(len(text), len(old)) and text[p] == old[p]:
        p += 1
    s = 0
    while s < min(len(text), len(old)) - p and text[-1 - s] == old[-1 - s]:
        s += 1
    a, b, at = p, len(text) - s, 0
    for x, t in zip(merged, texts):
        if x.get('type') == 'text' and not x['text'].get('link') and at <= a and b <= at + len(t):
            x['text']['content'] = t[:a - at] + old[p:len(old) - s] + t[b - at:]
            break
        at += len(t)
    else:
        return None
    if cue:
        merged = [_text('('), {'type': 'text', 'text': {'content': cue['plain_text'], 'link': cue['text']['link']},
                               'annotations': {}}, _text(') ')] + merged
    return merged


def fix_page(blocks, lang):
    """The script paragraph blocks of a live page -> {block id: new rich_text} for the blocks that change: one demo
    cue, right after the app's name in the paragraph where the first cue was (else where that cue was)."""
    orig = {b['id']: b[b['type']].get('rich_text', []) for b in blocks}
    cues = [(bid, n) for bid, r in orig.items() for n, x in enumerate(r) if _cue(x)]
    if not cues:
        return {}
    first_block, first_n = cues[0]
    link = orig[first_block][first_n]['text']['link']
    want = notion.cue_label_for(link['url'], lang)
    plain = lambda r: ''.join(x['text']['content'] if x.get('type') == 'text' else '' for x in r)
    rich = {bid: [_keep(x) for x in r] for bid, r in orig.items()}
    was = len(re.sub(r'\s*\($', '', plain(rich[first_block][:first_n])))  # where the first cue stood
    for bid in rich:  # every demo cue out, with its brackets
        rich[bid] = _drop_cues(rich[bid], [n for b, n in cues if b == bid])
    cue = [_text('('), {'type': 'text', 'text': {'content': want, 'link': link}, 'annotations': {}}, _text(') ')]
    label = TEXT[lang].get('screen_label', '')
    ids = list(rich)
    nxt = ids[ids.index(first_block) + 1] if ids.index(first_block) + 1 < len(ids) else None
    where = [first_block]
    if nxt and label and plain(rich[first_block]).lstrip().startswith(label):
        where.append(nxt)  # an on-screen text line: the creator says the name in the next paragraph
    for bid in where:
        text = plain(rich[bid])
        pos = anchor(text, label)
        if pos is None:
            continue
        after = ids[ids.index(bid) + 1] if ids.index(bid) + 1 < len(ids) else None
        if text[pos:].strip():
            rich[bid] = _insert(rich[bid], pos, cue)
        elif after:  # the name ends the paragraph: the cue starts the next one (as fix_spec does)
            rich[after] = _insert(rich[after], 0, cue)
        else:
            rich[first_block] = _insert(rich[first_block], was, cue)
        break
    else:
        rich[first_block] = _insert(rich[first_block], was, cue)
    def shape(r):  # what a reader sees: the text and where the links are (not how Notion splits it into pieces)
        text, links = '', []
        for x in r:
            t = x.get('plain_text') if 'plain_text' in x else (x['text']['content'] if x.get('type') == 'text' else '')
            url = ((x.get('text') or {}).get('link') or {}).get('url')
            if url:
                links.append((len(text), t, url))
            text += t or ''
        return text, links
    return {bid: r for bid, r in rich.items() if shape(orig[bid]) != shape(r)}
