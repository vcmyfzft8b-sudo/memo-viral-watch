"""Turn a viral Astra AI video into a Memo AI format page spec (same structure as our existing pages)."""
import os
import re

from . import llm
from .brand import CATEGORY, CUE, FACTS, OURS, OURS_SITE, SOURCE, SOURCE_DESC, says_source

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, '..', 'registry', 'examples')

from .markets import PRIMARY, TEXT, avoid_found

REQUIRED_LINE = TEXT[next(iter(TEXT))]['required_line']

SYSTEM = f"""You write creator instructions for {OURS} (an {CATEGORY}, https://{OURS_SITE}) UGC campaigns. You adapt
viral videos made by creators of {SOURCE_DESC}, a competing app, into the same format for {OURS}, in the creators'
language. Reply with JSON only."""

RULES = """RULES
- Output language for ALL creator-facing text (page_title, title_hook, script, visual_hook_first, extra_hook_lines,
  asset names/descriptions, directions): {lang}. Script style: {style}. Mirror the original SENTENCE BY SENTENCE:
  exactly one sentence of ours per sentence of the original, same order, about the same length - the whole script at
  most 110% of the original speech, add nothing. Same meaning, but build every sentence differently (other word
  order, question instead of statement, other words) - never a 1:1 transcription or literal translation, even more
  so when the original is already in {lang}. Name "{ours}" exactly where (and as often as) the original names
  {source}; if the original only shows the app ("this app here"), only show it too. A website/call to action at the
  end only if the original has one. Keep the hook idea and on-screen title punchy. Copy the STYLE and STRUCTURE of the
  example pages below, never their content.
- Replace {source} with {ours} everywhere (its website -> {site}). The word "{source}" (or "Astra") must not appear
  anywhere in your output.
- Concrete scores/grades/percentages the app shows become X (before) and Y (after) - creators read their own numbers.
- Adapt country-specific things to {country} (schools, exams like the matura, subjects, grades, places) when the
  original names local ones.
- Tone down promises nobody can guarantee (e.g. "guaranteed top grade", "pass any exam without studying").
- Every moment where the original video SHOWS the study app on screen gets cue "{cue}". Plain stage directions
  (e.g. surprised reaction, music, showing a notebook) use cue "direction" with the direction as text in asset_name.
  Otherwise cue null. Put the cue on the segment where that screen starts.
- Notebooks, textbooks, worksheets and the creator's own study material are NEVER assets: creators show their own.
- Public websites/apps the creator can simply open and film are NOT assets: use cue "direction" with a short
  direction and add one extra_hook_lines entry with the exact page to open.
- Only things a creator cannot make or open themselves count as assets (cue "asset", e.g. a recording of a full
  class group chat). For every asset, add one extra_hook_lines entry that says how to show it.
- Address creators neutrally (informal "you"), never with a gendered word for "creator".
- No voiceover videos (only on-screen text + music): set voiceover=false; each script segment is one text overlay.
- title_hook: the on-screen hook/title of the original, adapted to punchy {lang} (keep caps/emojis style).
- page_title: short {lang} hook for the Notion page name + one emoji at the end.
- visual_hook_first: one sentence telling the creator what to do in the first seconds, based on what the original
  creator does in the first 3 seconds (action/prop + speaking to camera + title on screen).
- return_to_camera: true if the original goes back to talking to the camera for the last line(s).
- extra_hook_lines: 0-2 extra lines only if the original needs special filming instructions. Never mention X/Y scores
  or going back to the camera at the end (both are added automatically). Every direction must refer to a line that is
  really in YOUR script (quote your own wording, not the original's). Never repeat the standard
  line about filming {ours} on the phone at every link and cutting loading times - it is added automatically."""


COUNTRY = {'sh': 'the whole region (Croatia, Bosnia and Herzegovina, Serbia, Montenegro) - prefer things every '
                 'student there knows; never Slovenian ones',
           'sl': 'Slovenia (Slovenian schools, the Slovenian matura, grades 1-5, Slovenian cities, shops and discounts)'}

SCHEMA = """Return JSON:
{"page_title": "...", "icon": "<one emoji>", "title_hook": "...", "voiceover": true,
 "script": [{"cue": "%s|asset|direction|null", "asset_name": "", "text": "...", "new_paragraph": false}],
 "visual_hook_first": "...", "return_to_camera": true, "extra_hook_lines": [],
 "has_scores": false, "assets_needed": [{"name": "...", "description": "<what it must show>"}],
 "registry_description": "<one English sentence describing the format, for matching future videos>",
 "summary_en": "<2 sentences: what the original video does and why it works>"}""" % CUE


def _examples():
    out = []
    for name in sorted(os.listdir(EXAMPLES)):
        with open(os.path.join(EXAMPLES, name)) as f:
            out.append(f'--- EXAMPLE PAGE {name} ---\n' + f.read())
    return '\n'.join(out)


def build_spec(video, transcript, frames, model, lang=PRIMARY, feedback=''):
    """video: tiktok.video_detail dict; transcript: soniox result; frames: [(seconds, path)]; lang: a markets.TEXT key."""
    T = TEXT[lang]
    rules = RULES.format(lang=T['lang_name'], style=T['style'], country=COUNTRY[lang], ours=OURS, source=SOURCE,
                         site=OURS_SITE, cue=CUE)
    timed = '\n'.join(f"[{s['start']:.1f}-{s['end']:.1f}s] {s['text']}" for s in transcript.get('segments', [])) or '(no speech)'
    content = [{'type': 'text', 'text': f"""Example pages in our layout (follow this style and structure, write in {T['lang_name']}):
{_examples()}

{rules}
{FACTS}

ORIGINAL VIDEO (@{video['handle']}, {video['views']} views, {video['duration']}s, language: {transcript.get('language') or '?'})
ON-SCREEN TEXT (TikTok text stickers): {video.get('sticker') or '-'}
CAPTION: {video.get('desc') or '-'}
SPEECH WITH TIMESTAMPS (Soniox):
{timed}

The following images are contact sheets of frames from the video; every tile is labelled with its timestamp in
seconds (red). Use them to see the visual hook, what is shown on screen and when the app appears.

{SCHEMA}{chr(10) + 'Your previous attempt was rejected: ' + feedback + ' Fix exactly that.' if feedback else ''}"""}]
    from . import media
    for t0, t1, path in media.contact_sheets(frames, os.path.dirname(frames[0][1])):
        content.append({'type': 'text', 'text': f'Frames {t0:.1f}s – {t1:.1f}s:'})
        content.append(llm.image_part(path))
    spec = llm.chat_json(model, SYSTEM, content, max_tokens=8000, temperature=0.4)
    for seg in spec.get('script', []):
        if seg.get('cue') in ('null', 'None', ''):
            seg['cue'] = None
    return spec


def hook_lines(spec, lang=PRIMARY):
    T = TEXT[lang]
    cues = {s.get('cue') for s in spec.get('script', [])}
    lines = [spec['visual_hook_first']]
    if CUE in cues:
        lines.append(T['app_line'])
    text = ' '.join(s['text'] for s in spec.get('script', []))
    has_x, has_y = bool(re.search(r'\bX\b', text)), bool(re.search(r'\bY\b', text))
    # the model's own extra lines must not repeat the standard lines (scores / back to camera)
    extra = [l for l in spec.get('extra_hook_lines', [])
             if not re.search(r'\bX\b|\bY\b', l) and not (spec.get('return_to_camera') and _similar(l, T['return_line']))]
    lines += extra
    if spec.get('return_to_camera'):
        lines.append(T['return_line'])
    if has_x or has_y:
        line = T['scores_line']
        if not (has_x and has_y):  # only one score in the script -> only name that one
            line = re.sub(r'X\s+(und|et|e|y|i|in)\s+Y', 'X' if has_x else 'Y', line)
        lines.append(line)
    return lines


def _similar(a, b):
    wa, wb = set(re.findall(r'\w{4,}', a.lower())), set(re.findall(r'\w{4,}', b.lower()))
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) >= 0.5


CYRILLIC = re.compile('[\u0400-\u04ff]')


def validate(spec, transcript, lang=PRIMARY):
    """Problems that block publishing (page goes to drafts instead)."""
    T = TEXT[lang]
    problems = []
    for key in ('page_title', 'title_hook', 'visual_hook_first', 'script'):
        if not spec.get(key):
            problems.append(f'missing {key}')
    texts = [spec.get('page_title', ''), spec.get('title_hook', ''), spec.get('visual_hook_first', '')]
    texts += [s.get('text', '') + ' ' + (s.get('asset_name') or '') for s in spec.get('script', [])]
    texts += spec.get('extra_hook_lines', [])
    blob = ' '.join(texts)
    if says_source(blob):
        problems.append(f'"{SOURCE}" appears in the page text')
    stop = set(T['stopwords'].split())
    words = re.findall(r"[a-zčćđšžäöüßàâçéèêëîïôûùüÿœñáíóú’']+", ' '.join(s.get('text', '') for s in spec.get('script', [])).lower())
    if words and sum(w in stop for w in words) / len(words) < 0.08:
        problems.append(f"script does not look {T['lang_name']}")
    if re.search(f"[{T['foreign']}]", blob.lower()):
        problems.append(f"non-{T['lang_name']} characters left in the text")
    if CYRILLIC.search(blob):
        problems.append('Cyrillic letters in the text (Latin script only)')
    avoid = avoid_found(lang, blob)
    if avoid:
        problems.append(f"{T['avoid_reason']}: {', '.join(avoid[:6])}")
    orig_words = len(transcript.get('text', '').split())
    new_words = sum(len(s.get('text', '').split()) for s in spec.get('script', []))
    if spec.get('voiceover', True) and orig_words >= 20:
        ratio = new_words / orig_words
        if not 0.8 <= ratio <= 1.12:
            problems.append(f'script length is {ratio:.0%} of the original (allowed 80–110%)')
    if not any(s.get('cue') == CUE for s in spec.get('script', [])):
        problems.append(f'no {OURS} moment in the script')
    return problems
