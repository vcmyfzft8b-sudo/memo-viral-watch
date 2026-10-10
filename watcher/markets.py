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
                  'country uses when a shared one exists; ti-form, a faithful translation that still sounds natural; '
                  'the speaker\'s own past-tense verbs in the FEMININE form (naučila sam, uslikala sam) - most creators '
                  'are women and a man simply switches the ending'),
        'address': 'ti (informal singular; "vi" only if the original speaks to a group - then consistently)',
        # One Balkan page serves four countries: names stay as in the original, the creator may swap them.
        'localize': '',
        'local_note': ('Ako scenarij spominje fakultete, škole, gradove, firme, cijene ili popuste iz neke zemlje, '
                       'slobodno ih zamijeni onima iz svoje zemlje.'),
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
        'hook_start': 'Napravi isti vizuelni hook kao u videu za inspiraciju: ',
        'hook_alt': 'Želiš drugi vizuelni hook? Izaberi jedan iz ',
        'draft_prefix': 'NACRT – ',
        'list_title': 'Koje videe snimaš (OBAVEZNO)', 'list_h1': 'Kako snimaš svoje videe',
        'list_heading': 'SNIMAJ SADA: ovi formati',
        'list_fire': ['Snimaj formate redom, od vrha prema dnu, i prođi cijelu listu. Drži se scenarija, vizuelnog hooka '
                      'i materijala na svakoj stranici.',
                      '**Samo ako neki video pređe {views} pregleda**, snimaj taj format iznova – dokle god je viralan. '
                      'Nakon toga nastavi s listom.'],
        'visual_rule': '**Vizuelni hook je obavezan u svakom videu!** Ideje imaš u ',
        'hot_suffix': '  ({n} videa s više od {views} pregleda u zadnjih 7 dana)',
        'holder': 'Svi formati', 'archive': 'Arhiva formata', 'guide': 'Memo AI – upute za kreatore',
        'discord': '@everyone 🔥 **Ovaj format upravo postaje viralan!**\n\n**{title}**\n\n{n} videa s više od {views} '
                   'pregleda u zadnjih 7 dana. 👉 Snimi ga **sada, kao sljedeći**.\n\nNaći ćeš ga na vrhu svoje liste '
                   'formata – pod upravo ovim naslovom.',
        'hot_header': 'Upravo postaje viralno – snimi ovo prvo',
        'stopwords': 'je i u da se na za ne su to od sa s što šta ali kao ili sam si mi ti ja ovo ovaj koji koja kako samo '
                     'još bi biti ima nije sve tako kad kada moj moja tvoj tvoja jer pa li već evo',
        # Characters that must not be left in the finished text (Polish/Czech/German/Spanish/Slovenian leftovers).
        'foreign': 'łąęńśźřůěťďňäöüßñ',
        # Unambiguous ekavian (Serbian-standard) forms: the pages are ijekavian.
        'avoid_reason': 'ekavian words (the pages are ijekavian)',
        'avoid_words': 'lepo lep lepa lepe vreme deca dece dete reč reči mesto mesta pesma videti razumeti hteo '
                       'htela devojka devojke mleko uvek gde ovde onde negde nigde sneg cena cene ponedeljak nedelja '
                       'nedelju belo beli bela primer primeri primera ocena ocene uspeh uspeha setiš seti setim '
                       'sećaš sećam seća sećanje celo cela ceo celu celi',
    },
    'sl': {
        'flag': '🇸🇮', 'name': 'Slovenija', 'lang_name': 'Slovenian',
        'style': ('casual spoken Slovenian the way Slovenian TEENAGERS talk on TikTok - relaxed and informal, not '
                  'textbook language: everyday words and fillers teens really use (e.g. "ful", "itak", "res", "kul", '
                  '"a veš", "pač", "tipa", "zihr", "js"/"jaz" as spoken), short punchy sentences, ti-form; still easy to '
                  'read and not overdone - a natural translation, never stiff or formal - and never Croatian/Serbian '
                  'words or forms (the source videos are Serbo-Croatian: "što", "koji", "već", "gdje" must become '
                  '"kaj", "ki", "že", "kje"); the speaker\'s own past-tense verbs in the FEMININE form (naučila sem, '
                  'slikala sem) - most creators are women and a man simply switches the ending; artificial '
                  'intelligence is always just "AI", never "umetna inteligenca"'),
        'address': 'ti (informal singular; "vi" only if the original speaks to a group - then consistently)',
        # Slovenian pages are localized: country-specific things become real Slovenian ones (user, 10 Oct 2026).
        'localize': ('Country-specific things are LOCALIZED for Slovenia: universities/faculties, schools, exams, '
                     'grades, cities, shops, brands, prices in other currencies, local discounts and programmes become '
                     'REAL Slovenian equivalents with their correct official names that make the same point (e.g. a '
                     'faculty of sport -> "Fakulteta za šport (Univerza v Ljubljani)", the matura -> "splošna matura", '
                     'a Serbian train discount -> the real Slovenian student discount). Never invent names, offers or '
                     'numbers that do not exist in Slovenia; everything else stays one to one.'),
        'local_note': '',
        'codes': ('sl',),
        'names': ('slovenian', 'slovene'),
        'video_heading': 'Video za navdih', 'source': 'Original na TikToku',
        'inspo_note': [
            '**Pomembno:** Posnemi svoj video po scenariju spodaj. Video za navdih ti pokaže le tempo, vzdušje, svetlobo '
            'in kote kamere – kako izgleda zaslon in kako pokažeš aplikacijo.',
            f'V videu je uporabljena aplikacija {SOURCE}. Naredi vse enako, le z aplikacijo {OURS}: pokaži vse, kar se vidi '
            f'v videu za navdih – odpri {OURS} v trenutkih, ko se odpre {SOURCE}, in ga pokaži na enak način. {SOURCE} se v '
            'tvojem videu ne sme nikjer videti ali slišati.'],
        'inspo_note_same': '**Pomembno:** Video za navdih je v slovenščini in prikazuje točno ta format – vzemi ga za zgled '
                           'za tempo, vzdušje, svetlobo, kote kamere in način, kako pokažeš aplikacijo. Povej pa naš '
                           'scenarij spodaj, ne besedila iz videa.',
        'title_h': 'NASLOV', 'script_h': '💬SCENARIJ', 'hook_h': '🎬 VIZUALNI HOOK', 'res_h': 'GRADIVO',
        'sub_voice': 'Samodejni podnapisi', 'sub_silent': 'Glasba iz knjižnice platforme, brez glasu',
        'silent_label': 'Besedilo na zaslonu – ne govori:',
        'asset_cue': '(📎 {name} – glej gradivo) ', 'asset_todo': 'še pripraviti',
        'app_line': f'Takoj ko se pojavi {OURS}, posnemi sebe, kako uporabljaš aplikacijo na telefonu – na vsakem mestu '
                    's povezavo v scenariju. Čakanje na nalaganje izreži.',
        'return_line': 'Za zadnji stavek se vrni v kamero.',
        'scores_line': 'X in Y v scenariju: preberi številko, ki ti jo pokaže aplikacija.',
        'required_line': '🚨👇 Vizualni hook je obvezen v vsakem videu!',
        'hook_start': 'Naredi enak vizualni hook kot v videu za navdih: ',
        'hook_alt': 'Želiš drugačen vizualni hook? Izberi ga v ',
        'draft_prefix': 'OSNUTEK – ',
        'list_title': 'Kakšne videe snemaš (OBVEZNO)', 'list_h1': 'Kako snemaš svoje videe',
        'list_heading': 'SNEMAJ ZDAJ: ti formati',
        'list_fire': ['Snemaj formate po vrsti, od zgoraj navzdol, in pojdi čez cel seznam. Drži se scenarija, vizualnega '
                      'hooka in gradiva na vsaki strani.',
                      '**Samo če kateri video preseže {views} ogledov**, ta format snemaj vedno znova – dokler je viralen. '
                      'Potem nadaljuj s seznamom.'],
        'visual_rule': '**Vizualni hook je obvezen v vsakem videu!** Ideje najdeš v ',
        'hot_suffix': '  ({n} videov z več kot {views} ogledi v zadnjih 7 dneh)',
        'holder': 'Vsi formati', 'archive': 'Arhiv formatov', 'guide': 'Memo AI – navodila za ustvarjalce',
        'discord': '@everyone 🔥 **Ta format ravno postaja viralen!**\n\n**{title}**\n\n{n} videov z več kot {views} '
                   'ogledi v zadnjih 7 dneh. 👉 Posnemi ga **zdaj, kot naslednjega**.\n\nNajdeš ga na vrhu svojega '
                   'seznama formatov – pod točno tem naslovom.',
        'hot_header': 'Ravno postaja viralno – posnemi najprej to',
        'stopwords': 'je in v da se na za ne so to od s z ki kaj kot ali sem si mi ti jaz ta tudi samo še bi biti ima ni '
                     'vse tako ko moj moja tvoj tvoja ker pa že zelo lahko kako',
        'foreign': 'ćđłąęńśźřůěťďňäöüßñ',
        'avoid_reason': 'words that do not belong on the Slovenian page (Croatian/Serbian forms; "umetna inteligenca" - say AI)',
        'avoid_words': 'što šta koji koja koje već ovo ovaj ova jer gdje gde nešto ništa uvijek uvek sutra trebaš '
                       'možeš puno umetna umetne umetni umetno',
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
    """Words that do not belong on this market's pages (ekavian forms on ijekavian pages, Serbo-Croatian on Slovenian)."""
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
