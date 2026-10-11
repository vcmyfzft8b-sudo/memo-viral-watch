"""Where the app comes in, in seconds (mode app-timing, read-only): for every live format, its original video is
transcribed with timestamps (Soniox) and looked at frame by frame; Claude marks every moment the original shows or
names its app - those are the moments our script puts Memo AI. Spoken mentions are also found directly in the
transcript. Prints one block per format; nothing in Notion changes.
"""
import re
import shutil
import tempfile

from . import llm, media, reword, soniox
from .brand import SOURCE_RE


def marked_script(page_id):
    """The page's script with every app link cue shown as [MEMO AI ON SCREEN]."""
    out = []
    for b in reword.script_blocks(page_id):
        parts = []
        for x in b[b['type']].get('rich_text', []):
            url = ((x.get('text') or {}).get('link') or {}).get('url') or ''
            parts.append('[MEMO AI ON SCREEN]' if 'memoai.eu' in url else x.get('plain_text', ''))
        out.append(re.sub(r'\(\s*\[MEMO AI ON SCREEN\]\s*\)', '[MEMO AI ON SCREEN]', ''.join(parts)))
    return '\n'.join(out)


def one(fmt, page_id, model):
    work = tempfile.mkdtemp(prefix='timing-')
    try:
        video = media.download(fmt['source_video'], work)
        dur = media.duration(video)
        try:
            tr = soniox.transcribe(media.audio(video, work))
        except Exception:
            tr = {'segments': [], 'text': ''}
        spoken = [round(s['start'], 1) for s in tr.get('segments', []) if SOURCE_RE.search(s.get('text', ''))
                  or re.search(r'\bmemo\s*a\.?\s*i\b', s.get('text', ''), re.I)]
        timed = '\n'.join(f"[{s['start']:.1f}-{s['end']:.1f}s] {s['text']}" for s in tr.get('segments', [])) or '(no speech)'
        content = [{'type': 'text', 'text': f"""ORIGINAL VIDEO ({dur:.0f} s) of a UGC format for a study app. The original
promotes a study app (Astra AI, Studyflash, Turbo AI or Memo AI itself). Our script uses Memo AI where the original
uses its app.

SPEECH WITH TIMESTAMPS:
{timed}

OUR SCRIPT (in another language; [MEMO AI ON SCREEN] = where Memo AI is shown):
{marked_script(page_id)[:3000]}

The images are contact sheets of frames, each tile labelled with its second. Find, in seconds of the ORIGINAL video,
every moment the app is SHOWN on screen (phone/laptop screen, logo, app UI) or NAMED (spoken or as on-screen text).
Return JSON {{"first_second": <number>, "moments": [{{"from": <s>, "to": <s>, "what": "<short, English>"}}],
"share_of_video": "<e.g. last 30 %>"}}"""}]
        frames = media.frames(video, work)
        for t0, t1, path in media.contact_sheets(frames, work):
            content.append({'type': 'text', 'text': f'Frames {t0:.1f}s - {t1:.1f}s:'})
            content.append(llm.image_part(path))
        r = llm.chat_json(model, 'You time video moments precisely. Reply with JSON only.', content, max_tokens=2000)
        return {'duration': round(dur), 'spoken': spoken, **r}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run(cfg, fmts, page_of, rank_ids):
    by = {f['id']: f for f in fmts}
    first_market = list(cfg['markets'])
    for n, fid in enumerate(rank_ids, 1):
        f = by[fid]
        key = next((k for k in first_market if page_of(f, k)), None)
        if not key or not f.get('source_video'):
            continue
        try:
            r = one(f, page_of(f, key), cfg['models']['build'])
            moments = '; '.join(f"{m['from']}-{m['to']} s {m['what']}" for m in r.get('moments', []))
            print(f"TIMING #{n} {f['title']} | {r['duration']} s | first: {r.get('first_second')} s | spoken: "
                  f"{r['spoken'] or '-'} | {moments} | {r.get('share_of_video', '')}", flush=True)
        except Exception as e:
            print(f"TIMING #{n} {f['title']} | failed: {str(e)[:150]}", flush=True)
