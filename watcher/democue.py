"""One demo cue per script, right after the app is named (user's rule, 16 Oct 2026).

Creators play the Memo AI demo recording from the 🎥 mark to its end and talk over it, so a script has exactly one
demo cue: right after the creator says "Memo AI" (or "this app") in the paragraph where the app comes in - after the
end of that sentence when it is short, else right after the name. Later demo cues are dropped. A format with its own
app page (the oral quiz) keeps its cues: this is only for the demo recordings.

`fix_spec` does it on a script spec (registry/approved_scripts.json, page rendering); `fix_page` on a live page.
"""
import re

from . import notion
from .brand import CUE, is_demo_link
from .markets import TEXT

APP_RE = re.compile(r'Memo\s?AI|\b(?:ta|tale|tole|ovu|ova|ovo|ovom|tu|to)\s+(?:app|aplikacij[aeiou]\w*)\b', re.I)
NEAR = 60  # a sentence that ends this soon after the name: the cue goes after its end
END_RE = re.compile(r'[.:!?]+[»«“”"\')]*')


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
    pos = m.end()
    return pos + 1 if text[pos:pos + 1] == ',' else pos


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
    for i in range(start, end):
        pos = anchor(out[i].get('text') or '', label)
        if pos is None:
            continue
        text = out[i]['text']
        head, tail = text[:pos].rstrip(), text[pos:].strip()
        if i == first and not head:
            return out  # the cue is already right before the name
        out[first] = dict(out[first], cue=None)
        if not tail:  # the name ends the segment: the cue goes on the next one in this paragraph
            if i + 1 < end:
                out[i + 1] = dict(out[i + 1], cue=CUE)
                return out
            out[first] = dict(out[first], cue=CUE)  # nothing after it here: keep the cue where it was
            return out
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
    for bid, n in reversed(cues):  # every demo cue out, with its brackets
        items = rich[bid]
        items[n] = None
        if n > 0 and items[n - 1] and items[n - 1].get('type') == 'text':
            items[n - 1]['text']['content'] = re.sub(r'\s*\($', ' ', items[n - 1]['text']['content'])
        if n + 1 < len(items) and items[n + 1] and items[n + 1].get('type') == 'text':
            items[n + 1]['text']['content'] = re.sub(r'^\)\s*', '', items[n + 1]['text']['content'])
    for bid in rich:
        rich[bid] = [x for x in rich[bid] if x and not (x.get('type') == 'text' and x['text']['content'].strip() == '')]
        if rich[bid] and rich[bid][0].get('type') == 'text':
            rich[bid][0]['text']['content'] = rich[bid][0]['text']['content'].lstrip()
    cue = [_text('('), {'type': 'text', 'text': {'content': want, 'link': link}, 'annotations': {}}, _text(') ')]
    text = plain(rich[first_block])
    pos = anchor(text, TEXT[lang].get('screen_label', ''))
    if pos is not None and not text[pos:].strip():
        pos = None  # the name ends the paragraph: the cue stays where it was (as fix_spec does)
    rich[first_block] = _insert(rich[first_block], was if pos is None else pos, cue)
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
