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
        # The ⚠️ note under the inspiration video. Its first 30 characters tell "same language" (…_same) from "other
        # language" apart (audit._note_is_same) - keep those starts as they are.
        'inspo_note': [
            '**Važno:** Snimi svoj video po scenariju ispod. Video za inspiraciju je od drugog brenda i nije video koji '
            'trebaš napraviti. Od njega što vjernije kopiraj ukupnu atmosferu (vibe), uglove kamere, način snimanja, montažu '
            'i trenutke u kojima se pokazuje aplikacija (demo) – za to služe videi za inspiraciju.',
            f'**OBAVEZNO:** kad pričaš o {OURS}, samo otvori aplikaciju na laptopu preko linka memoai.eu/creator i snimaj '
            'kako prolaziš kroz nju i pokazuješ šta sve može – ubaciš PDF, PowerPoint ili snimak predavanja, pa pokažeš '
            'bilješke, flash kartice, kviz, probni test i druge funkcije koje aplikacija ima. Snimi to isto kao u videu za inspiraciju. Druga aplikacija iz videa '
            'se u tvom videu nigdje ne smije vidjeti ni čuti.'],
        'record_note': (f'**OBAVEZNO:** kad pričaš o {OURS}, samo otvori aplikaciju na laptopu preko linka '
                        'memoai.eu/creator i snimaj kako prolaziš kroz nju i pokazuješ šta sve može – ubaciš PDF, '
                        'PowerPoint ili snimak predavanja, pa pokažeš bilješke, flash kartice, kviz, probni test i druge funkcije koje aplikacija ima. Snimi to '
                        'isto kao u videu za inspiraciju.'),
        'cue_verb': 'Snimi',
        'pitch': ('u nju ubaciš PDF-ove ili PowerPoint prezentacije sa predavanja, a možeš i snimiti predavanje i taj audio '
                  'snimak ubaciti u Memo AI. Dobiješ bilješke, flash kartice, testove, kvizove i još mnogo drugih funkcija, '
                  's kojima sve naučiš na jako jednostavan način.'),
        'screen_label': 'Tekst na ekranu:',
        'logo_line': '📎 Memo AI logo (prozirna pozadina, visoka kvaliteta) – slika ispod; koristi ga u videu ako želiš.',
        'record_rule': ('obavezno: na svakom mjestu označenom sa 🎥 samo otvori Memo AI na laptopu i snimaj kako prolaziš '
                        'kroz aplikaciju i pokazuješ šta sve može (PDF, PowerPoint ili snimak predavanja → bilješke, flash '
                        'kartice, kviz, probni test i druge funkcije), kao u videu za inspiraciju.'),
        'inspo_note_same': '**Važno:** Video za inspiraciju je na našem jeziku i pokazuje upravo ovaj format, ali je od '
                           'drugog brenda i nije video koji trebaš napraviti. Od njega što vjernije kopiraj ukupnu atmosferu (vibe), '
                           'uglove kamere, način snimanja, montažu i trenutke u kojima se pokazuje aplikacija (demo) – za to '
                           'služe videi za inspiraciju. Izgovori naš scenarij ispod, ne tekst iz videa.',
        # inspiration video that is already a Memo AI video (our own creators' videos, added by hand)
        'inspo_note_own': f'**Važno:** Snimi svoj video po scenariju ispod. Video za inspiraciju je već {OURS} video. Od '
                          'njega što vjernije kopiraj ukupnu atmosferu (vibe), uglove kamere, način snimanja, montažu i trenutke u '
                          'kojima se pokazuje aplikacija (demo).',
        'inspo_note_own_same': f'**Važno:** Video za inspiraciju je na našem jeziku, pokazuje upravo ovaj format i već je '
                               f'{OURS} video. Kopiraj ga što vjernije: ukupnu atmosferu (vibe), uglove kamere, način snimanja, '
                               'montažu i trenutke u kojima se pokazuje aplikacija (demo). Izgovori naš scenarij ispod.',
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
        'style': ('natural, casual spoken Slovenian as a young creator talks on TikTok, but always grammatically CORRECT '
                  'standard Slovenian (user, 11 Oct 2026): no shortened colloquial spellings ("tko", "tok", "al", "blo", '
                  '"enga", "okol", "zdajle", "js", infinitives like "končat"/"prit" -> "tako", "toliko", "ali", "bilo", '
                  '"enega", "okoli", "zdaj", "jaz", "končati", "priti"); short clear sentences, ti-form; never stiff or '
                  'formal, and never Croatian/Serbian words or forms (the source videos are Serbo-Croatian: "što", '
                  '"koji", "već", "gdje" must become "kaj", "ki", "že", "kje"); follow on TikTok = "zafolovat" / '
                  '"zafolovaš", never "zapratit"; the speaker\'s own past-tense verbs in the FEMININE form (naučila sem, '
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
            '**Pomembno:** Posnemi svoj video po scenariju spodaj. Video za navdih je od druge znamke in ni video, ki ga '
            'moraš posneti. Od njega čim bolj natančno kopiraj splošno vzdušje (vibe), kote kamere, način snemanja, montažo in trenutke, '
            'ko se pokaže aplikacija (demo) – za to so videi za navdih.',
            f'**OBVEZNO:** ko govoriš o {OURS}, samo odpri aplikacijo na prenosniku prek povezave memoai.eu/creator in '
            'posnemi, kako greš skozi njo in pokažeš, kaj vse zna – naložiš PDF, PowerPoint ali posnetek predavanja, nato '
            'pokažeš zapiske, učne kartice, kviz, poskusni test in druge funkcije, ki jih ima aplikacija. Posnemi to enako kot v videu za navdih. Druga aplikacija '
            'iz videa se v tvojem videu ne sme nikjer videti ali slišati.'],
        'record_note': (f'**OBVEZNO:** ko govoriš o {OURS}, samo odpri aplikacijo na prenosniku prek povezave '
                        'memoai.eu/creator in posnemi, kako greš skozi njo in pokažeš, kaj vse zna – naložiš PDF, '
                        'PowerPoint ali posnetek predavanja, nato pokažeš zapiske, učne kartice, kviz, poskusni test in druge funkcije, ki jih ima aplikacija. '
                        'Posnemi to enako kot v videu za navdih.'),
        'cue_verb': 'Posnemi',
        'pitch': ('vanjo naložiš PDF-je ali PowerPointe s predavanj, lahko pa predavanje tudi posnameš in zvočni posnetek '
                  'naložiš v Memo AI. Ven dobiš zapiske, učne kartice, teste, kvize in še veliko drugih funkcij, s katerimi '
                  'se vse naučiš na zelo preprost način.'),
        'screen_label': 'Besedilo na zaslonu:',
        'logo_line': '📎 Logotip Memo AI (prozorno ozadje, visoka kakovost) – slika spodaj; uporabi ga v videu, če želiš.',
        'record_rule': ('obvezno: na vsakem mestu, označenem z 🎥, samo odpri Memo AI na prenosniku in posnemi, kako greš '
                        'skozi aplikacijo in pokažeš, kaj vse zna (PDF, PowerPoint ali posnetek predavanja → zapiski, učne '
                        'kartice, kviz, poskusni test in druge funkcije), kot v videu za navdih.'),
        'inspo_note_same': '**Pomembno:** Video za navdih je v slovenščini in prikazuje točno ta format, ampak je od druge '
                           'znamke in ni video, ki ga moraš posneti. Od njega čim bolj natančno kopiraj splošno vzdušje (vibe), kote '
                           'kamere, način snemanja, montažo in trenutke, ko se pokaže aplikacija (demo) – za to so videi za '
                           'navdih. Povej naš scenarij spodaj, ne besedila iz videa.',
        'inspo_note_own': f'**Pomembno:** Posnemi svoj video po scenariju spodaj. Video za navdih je že {OURS} video. Od '
                          'njega čim bolj natančno kopiraj splošno vzdušje (vibe), kote kamere, način snemanja, montažo in trenutke, ko se '
                          'pokaže aplikacija (demo).',
        'inspo_note_own_same': f'**Pomembno:** Video za navdih je v slovenščini, prikazuje točno ta format in je že {OURS} '
                               'video. Čim bolj natančno ga posnemi: splošno vzdušje (vibe), kote kamere, način snemanja, montažo in '
                               'trenutke, ko se pokaže aplikacija (demo). Povej naš scenarij spodaj.',
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
                       'možeš puno umetna umetne umetni umetno zaprati zapratiš zapratite zapratit zapratiti zaprati',
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


EARLY_WORDS = 50  # Memo AI comes in at about 15 s: at most this many spoken words before the first app cue


def conversion_rules(lang, own_example=False):
    """How every script is built (user's rules, 12 Oct 2026, from the scripts reworked together): the original's viral
    hook, Memo AI early (~15 s) with the standard pitch, then the rest tightened. Our own creators' videos (already
    built this way) stay word for word."""
    T = TEXT[lang]
    if own_example:
        return ('The example is already a Memo AI video of our own creators: keep its words almost one to one (same '
                'sentences, order, jokes); only spelling/grammar and the language rules may change.')
    return f"""HOW OUR SCRIPTS ARE BUILT (user's rules - every script follows them):
1. HOOK: keep the original's hook (first sentence(s), on-screen title, premise) almost word for word - that is what
   made it go viral.
2. MEMO AI EARLY: Memo AI comes in at about 15 seconds - after at most about 40 spoken words (never more than
   {EARLY_WORDS}) - at a point that makes sense in the story: as the secret, the solution, the next tip or list item,
   the thing the creator uses instead, the friend's trick. Never only at the end. In list formats put one or two real
   items before it and keep the best item (e.g. no. 1) for after it.
3. PITCH: where Memo AI comes in, say what it does in these words (adapted slightly to the sentence): "{T['pitch']}"
4. REST: then the rest of the original's beats, jokes, payoff and call to action in the same order, tightened (cut
   filler and app click-walkthroughs - the creator records the app instead). Aim for under about 60 seconds.
5. TRUTH: only real Memo AI features; never another app's features or company facts (founding year, prices, codes):
   leave such parts out instead of inventing.
6. FORM: on-screen sticker texts as their own lines ("{T['screen_label']} ..."); a dialogue with the app's voice as
   "Memo AI: ..." / "Ti: ..." lines."""


def words_before_app(script, cue):
    """Spoken words before the first segment with the app cue (None if there is none)."""
    n = 0
    for seg in script or []:
        if seg.get('cue') == cue:
            return n
        n += len(re.findall(r'\w+', seg.get('text') or ''))
    return None


def own(fmt, lang):
    """Is the example on this language's page already a Memo AI video? fmt['own_brand'] is True (every page) or a
    {lang: True} map (e.g. only the Slovenian page shows one of our own creators' videos)."""
    o = (fmt or {}).get('own_brand')
    return bool(o.get(lang)) if isinstance(o, dict) else bool(o)


def of(mkts, fmt):
    """The markets a format is made for: all, or only those in fmt['only_markets'] (e.g. a Slovenian-only format added
    by hand). Every per-format loop over the markets goes through this."""
    only = (fmt or {}).get('only_markets')
    return [mk for mk in mkts if not only or mk['key'] in only]


def load(cfg):
    """[{key, lang, list_page, holder_page, archive_page, visual_hook_lab, discord_env, T}] for the enabled markets."""
    out = []
    for key, m in cfg['markets'].items():
        if not m.get('enabled', True):
            continue
        out.append({'key': key, **m, 'T': TEXT[m['lang']]})
    return out
