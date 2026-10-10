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
- The script is the ORIGINAL video, transcribed and - if needed - translated into {lang}, almost one to one: the same
  sentences in the same order with the same meaning, words, jokes, numbers, places and claims; nothing added, nothing
  left out, nothing reworded. Only these change: "{source}" (and any other study app the video promotes) becomes
  "{ours}" - exactly where and as often as the original names it -, its website becomes {site}, and an app feature
  {ours} does not have becomes the closest real {ours} feature (only those words). If the original only shows the
  app ("this app here"), only show it too. Language: {style}. If the original is already in {lang}, the script is its
  transcript with only those changes (and the spelling rules of the language).
- {localize}
- Copy the STYLE and STRUCTURE of the example pages below (layout, cues, directions), never their content.
- The word "{source}" (or "Astra") must not appear anywhere in your output.
- Every moment where the original video SHOWS the study app on screen gets cue "{cue}". Plain stage directions
  (e.g. surprised reaction, music, showing a notebook) use cue "direction" with the direction as text in asset_name.
  Otherwise cue null. Put the cue on the segment where that screen starts.
- Notebooks, textbooks, worksheets and the creator's own study material are NEVER assets: creators show their own.
- Public websites/apps the creator can simply open and film are NOT assets: use cue "direction" with a short
  direction.
- Only things a creator cannot make or open themselves count as assets (cue "asset", e.g. a recording of a full
  class group chat).
- Address creators neutrally (informal "you"), never with a gendered word for "creator".
- No voiceover videos (only on-screen text + music): set voiceover=false; each script segment is one text overlay.
- title_hook: the on-screen hook/title of the original, translated one to one into {lang} (same caps/emojis).
- page_title: short {lang} hook for the Notion page name + one emoji at the end.
- visual_hook_first: ONE sentence (two at most) that tells the creator to copy the example video's visual hook:
  exactly what the original creator does in the first seconds (action, prop, where they look, what is on screen),
  e.g. "<start> you sit at the desk, slowly peel a mandarin and look into the camera while the title is on screen."
  Write it in {lang}. Nothing else goes into this field (no filming tips, no app instructions).
- return_to_camera / extra_hook_lines: leave false / empty (the visual hook section holds only the sentence above)."""


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


def build_spec(video, transcript, frames, model, lang=PRIMARY, feedback='', brief=''):
    """video: tiktok.video_detail dict; transcript: soniox result; frames: [(seconds, path)]; lang: a markets.TEXT key."""
    T = TEXT[lang]
    rules = RULES.format(lang=T['lang_name'], style=T['style'], country=COUNTRY[lang], ours=OURS, source=SOURCE,
                         site=OURS_SITE, cue=CUE, localize=T.get('localize') or
                         'Names of universities, schools, cities, shops etc. stay exactly as in the original.')
    timed = '\n'.join(f"[{s['start']:.1f}-{s['end']:.1f}s] {s['text']}" for s in transcript.get('segments', [])) or '(no speech)'
    content = [{'type': 'text', 'text': f"""Example pages in our layout (follow this style and structure, write in {T['lang_name']}):
{_examples()}

{rules}
{FACTS}
{('NOTE FROM THE CAMPAIGN TEAM for this format (follow it): ' + brief) if brief else ''}

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
        if seg.get('cue') == 'asset' and re.search(r'memo\s*ai', seg.get('asset_name') or '', re.I):
            seg['cue'], seg['asset_name'] = CUE, ''  # the app itself is never a "material" - it is the app link cue
    return spec


def hook_lines(spec, lang=PRIMARY):
    """The visual hook section: one (at most two) sentence(s) - copy the example's opening. The line offering the
    Visual Hook Lab instead is added by notion.page_blocks."""
    T = TEXT[lang]
    first = (spec.get('visual_hook_first') or '').strip()
    if first and not first.lower().startswith(T['hook_start'].strip().lower()[:20]):
        first = T['hook_start'] + first[0].lower() + first[1:]
    return [first] if first else []


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
