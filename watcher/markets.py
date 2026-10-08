"""Markets: Notion pages, language texts and per-market data keys.

Today there is one market: the Balkans (Serbia, Croatia, Bosnia and Herzegovina, Montenegro), with every page in
Serbo-Croatian - Latin script, ijekavian, words the whole region understands. The code keeps the multi-market shape
(one shared format list, one page per market), so another market can be added in config.json + TEXT later.
"""
import json
import os
import re

from .brand import OURS, SOURCE

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

TEXT = {
    'sh': {
        'flag': '🇧🇦🇭🇷🇷🇸🇲🇪', 'name': 'Balkan', 'lang_name': 'Serbo-Croatian',
        # What the model and the reviewers are told about the language.
        'style': ('casual spoken Serbo-Croatian like a real TikTok creator from the region - Latin script ONLY (never '
                  'Cyrillic), IJEKAVIAN forms (vrijeme, lijepo, gdje, dijete, uvijek, mjesto, cijena), and words the '
                  'whole region understands (Croatia, Bosnia and Herzegovina, Montenegro, Serbia): avoid words only one '
                  'country uses when a shared one exists; ti-form, natural, not formal, not a literal translation; '
                  'the speaker\'s own past-tense verbs in the FEMININE form (naučila sam, uslikala sam) - most creators '
                  'are women and a man simply switches the ending'),
        'address': 'ti (informal singular; "vi" only if the original speaks to a group - then consistently)',
        # Soniox language codes and the language names a model may return for this market's videos.
        'codes': ('sr', 'hr', 'bs', 'sh', 'cnr', 'me'),
        'names': ('serbo-croatian', 'serbian', 'croatian', 'bosnian', 'montenegrin', 'bcs', 'bcms'),
        'video_heading': 'Video za inspiraciju', 'source': 'Original na TikToku',
        'inspo_note': [
            '**Važno:** Snimi svoj video po scenariju ispod. Video za inspiraciju ti pokazuje samo tempo, atmosferu, '
            'svjetlo i uglove kamere – kako izgleda ekran i kako pokazuješ aplikaciju.',
            f'U videu se koristi {SOURCE}. Napravi sve isto, samo s aplikacijom {OURS}: pokaži sve što se vidi u videu za '
            f'inspiraciju – otvori {OURS} u trenucima kad se otvara {SOURCE} i pokaži ga na isti način. {SOURCE} se u tvom '
            'videu nigdje ne smije vidjeti ni čuti.'],
        'inspo_note_same': '**Važno:** Video za inspiraciju je na našem jeziku i pokazuje upravo ovaj format – uzmi ga kao '
                           'uzor za tempo, atmosferu, svjetlo, uglove kamere i način na koji pokazuješ aplikaciju. Ali '
                           'izgovori naš scenarij ispod, ne tekst iz videa.',
        'title_h': 'NASLOV', 'script_h': '💬SCENARIJ', 'hook_h': '🎬 VIZUELNI HOOK', 'res_h': 'MATERIJALI',
        'sub_voice': 'Automatski titlovi', 'sub_silent': 'Muzika iz biblioteke platforme, bez glasa',
        'silent_label': 'Tekst na ekranu – ne izgovaraj:',
        'asset_cue': '(📎 {name} – vidi materijale) ', 'asset_todo': 'tek treba pripremiti',
        'app_line': f'Čim se pojavi {OURS}, snimaj sebe kako koristiš aplikaciju na telefonu – na svakom mjestu s linkom '
                    'u scenariju. Izreži vrijeme učitavanja.',
        'return_line': 'Za zadnju rečenicu vrati se u kameru.',
        'scores_line': 'X i Y u scenariju: pročitaj broj koji ti aplikacija pokaže.',
        'required_line': '🚨👇 Vizuelni hook je obavezan u svakom videu!',
        'draft_prefix': 'NACRT – ',
        'list_title': 'Koje videe snimaš (OBAVEZNO)', 'list_h1': 'Kako snimaš svoje videe',
        'list_heading': 'SNIMAJ SADA: ovi formati',
        'list_fire': ['Snimaj formate redom, od vrha prema dnu, i prođi cijelu listu. Drži se scenarija, vizuelnog hooka '
                      'i materijala na svakoj stranici.',
                      '**Samo ako neki video pređe {views} pregleda**, snimaj taj format iznova – dokle god je viralan. '
                      'Nakon toga nastavi s listom.'],
        'visual_rule': '**Vizuelni hook je obavezan u svakom videu!** Ideje imaš u ',
        'hot_suffix': '  ({n} videa s više od {views} pregleda u zadnjih 7 dana)',
        'holder': 'Svi formati', 'archive': 'Arhiva formata',
        'discord': '@everyone 🔥 **Ovaj format upravo postaje viralan!**\n\n**{title}**\n\n{n} videa s više od {views} '
                   'pregleda u zadnjih 7 dana. 👉 Snimi ga **sada, kao sljedeći**.\n\nNaći ćeš ga na vrhu svoje liste '
                   'formata – pod upravo ovim naslovom.',
        'hot_header': 'Upravo postaje viralno – snimi ovo prvo',
        'stopwords': 'je i u da se na za ne su to od sa s što šta ali kao ili sam si mi ti ja ovo ovaj koji koja kako samo '
                     'još bi biti ima nije sve tako kad kada moj moja tvoj tvoja jer pa li već evo',
        # Characters that must not be left in the finished text (Polish/Czech/German/Spanish/Slovenian leftovers).
        'foreign': 'łąęńśźřůěťďňäöüßñ',
        # Unambiguous ekavian (Serbian-standard) forms: the pages are ijekavian.
        'avoid_words': 'lepo lep lepa lepe vreme deca dece dete reč reči mesto mesta pesma videti razumeti hteo '
                       'htela devojka devojke mleko uvek gde ovde onde negde nigde sneg cena cene ponedeljak nedelja '
                       'nedelju belo beli bela primer primeri primera ocena ocene uspeh uspeha',
    },
}
# Slovenian looks a lot like Serbo-Croatian in captions; it is only used to tell the two apart (Slovenia is not one of
# our countries, and Astra AI comes from there).
SLOVENIAN_STOPWORDS = set('in je da se na za ne so to od s z ki kaj kot ali sem si mi ti jaz ta tudi samo še bi biti ima '
                          'ni vse tako ko moj tvoj ker pa že zelo lahko kako sploh'.split())


def _primary():
    with open(os.path.join(ROOT, 'config.json')) as f:
        return next(iter(json.load(f)['markets']))


PRIMARY = _primary()  # the first market in config.json: its page is fmt['page_id'], its keys have no suffix


def fkey(m):
    """Field holding a video's format id for this market ('format' for the first market)."""
    return 'format' if m == PRIMARY else f'format_{m}'


def jkey(m):
    return 'judged' if m == PRIMARY else f'judged_{m}'


def ckey(m):
    return 'format_checked' if m == PRIMARY else f'format_checked_{m}'


def formats_file(m):
    return 'formats.json' if m == PRIMARY else f'formats_{m}.json'


def lang_matches(lang, language):
    """Is a language name/code (from Soniox or a model) this market's language? 'Croatian', 'sr', 'Bosnian' -> 'sh'."""
    t = TEXT[lang]
    x = str(language or '').strip().lower()
    return bool(x) and (x[:3].rstrip('-_') in t['codes'] or x[:2] in t['codes'] or any(n in x for n in t['names']))


def avoid_found(lang, text):
    """Words of the other standard (ekavian forms on ijekavian pages)."""
    bad = set(TEXT[lang].get('avoid_words', '').split())
    return sorted({w for w in re.findall(r'\w+', (text or '').lower()) if w in bad})


def load(cfg):
    """[{key, lang, list_page, holder_page, archive_page, visual_hook_lab, discord_env, T}] for the enabled markets."""
    out = []
    for key, m in cfg['markets'].items():
        if not m.get('enabled', True):
            continue
        out.append({'key': key, **m, 'T': TEXT[m['lang']]})
    return out
