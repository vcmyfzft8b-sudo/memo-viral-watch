"""One-time Notion setup (mode setup-notion): builds the page structure the watcher works with, in the Notion
workspace of NOTION_TOKEN, under the one page shared with the integration (or NOTION_ROOT_PAGE):

  <shared page>
  ├── SNIMAJ SADA: ovi formati      the list creators work from (🔥 instructions, ▶️ formats, 🚨 rule)
  ├── Svi formati                   every live format page
  ├── Arhiva formata                formats taken out of the list (nothing is ever deleted)
  ├── Visual Hook Lab               ideas for the first seconds of a video
  └── Viral-Radar (interno)         log + staging: new pages wait here until they pass the checks

The page ids go to state/notion.json (main.load_config reads them). Running it again changes nothing.
"""
import os

from . import hot, notion, state
from .brand import OURS
from .markets import TEXT

HOOK_IDEAS = [
    'Kreni usred radnje: zatvaraš udžbenik uz glasan udarac i odmah gledaš u kameru.',
    'Pokaži pun stol – knjige, flomasteri, papiri – i jednim pokretom sve skloni u stranu.',
    'Drži telefon s ekranom prema kameri, kao da nekome pokazuješ tajnu.',
    'Snimi se odozgo dok listaš papire pune precrtanih bilješki, pa naglo stani.',
    'Šapni prvu rečenicu tik uz kameru, kao da si u učionici, pa se odmakni.',
    'Uđi u kadar s ruksakom na jednom ramenu, kao da si upravo stigao/la iz škole.',
    'Pokaži sat ili alarm na telefonu (npr. 23:47) prije prve rečenice.',
    'Baci list s lošom ocjenom (bez stvarnog imena) na stol prema kameri.',
    'Počni s glavom na stolu između knjiga, podigni pogled tek na prvu riječ.',
    'Prvi kadar: naslov na ekranu preko tvog lica u krupnom planu, bez riječi 2 sekunde.',
]


def _root():
    if os.environ.get('NOTION_ROOT_PAGE'):
        return os.environ['NOTION_ROOT_PAGE'].strip().split('-')[-1].split('?')[0][-32:]
    found = notion.api('POST', '/search', {'filter': {'property': 'object', 'value': 'page'}, 'page_size': 100})['results']
    top = [p for p in found if (p.get('parent') or {}).get('type') == 'workspace' and not p.get('archived')]
    if len(top) != 1:
        names = [''.join(x['plain_text'] for x in next((v['title'] for v in p['properties'].values()
                                                      if v['type'] == 'title'), [])) for p in top]
        raise SystemExit(f'setup-notion: share exactly ONE top page with the integration (found {len(top)}: {names}) '
                         'or set NOTION_ROOT_PAGE')
    return top[0]['id']


def _page(parent, title, icon, blocks=()):
    return notion.create_page(parent, title, icon, list(blocks))['id']


def list_blocks(T, lab, holder, viral):
    """The format list, laid out 1:1 like the Parakeet AI (Resume Maker) list: H1 · H2 · red 🔥 instructions · empty
    line · (▶️ formats, written by notion.set_order) · empty line · red 🚨 Visual Hook rule · empty line · 📁 toggle
    with all format pages."""
    fire = [notion.rt(T['list_fire'][0]), notion.rt('\n')] + notion.md(T['list_fire'][1].format(views=viral))
    rule = notion.md(T['visual_rule']) + [notion.mention(lab), notion.rt('.')]
    return [notion.block('heading_1', [notion.rt(T['list_h1'])]),
            notion.block('heading_2', [notion.rt(T['list_heading'])]),
            notion.block('callout', fire, icon={'type': 'emoji', 'emoji': '🔥'}, color='red_background'),
            notion.block('paragraph', []),
            notion.block('callout', rule, icon={'type': 'emoji', 'emoji': '🚨'}, color='red_background'),
            notion.block('paragraph', []),
            notion.block('toggle', [notion.rt('📁 ' + T['holder'])],
                         children=[{'object': 'block', 'type': 'link_to_page',
                                    'link_to_page': {'type': 'page_id', 'page_id': holder}}])]


def relayout_list(cfg):
    """Rebuild an existing list page in the current layout (title, headings, boxes, 📁 toggle); the ▶️ formats are
    written again by the re-sort afterwards."""
    pages = state.load('notion.json', {})
    viral = hot.views_text(cfg['thresholds']['viral_views'])
    for key, m in cfg['markets'].items():
        T, mp = TEXT[m['lang']], pages['markets'][key]
        lab = mp['visual_hook_lab'].rstrip('/').split('/')[-1].split('-')[-1]
        notion.replace_content(mp['list_page'], list_blocks(T, lab, mp['holder_page'], viral))
        notion.api('PATCH', f"/pages/{mp['list_page']}", {'icon': {'type': 'emoji', 'emoji': '👉'},
                                                          'properties': {'title': {'title': [notion.rt(T['list_title'])]}}})
        print('list page rebuilt:', key, mp['list_page'])


def notion_pages(cfg):
    """Creates what is missing (run again after adding a market): the radar, and per market a guide page
    ("🇸🇮 Memo AI – navodila za ustvarjalce", like Parakeet's per-country Creator-Anleitung) holding its list, all format
    pages, archive and Visual Hook Lab. Pages made before the guide pages existed are moved into their guide."""
    pages = state.load('notion.json', {})
    root = pages.get('root') or _root()
    pages['root'] = root
    viral = hot.views_text(cfg['thresholds']['viral_views'])
    if not pages.get('radar_page'):
        pages['radar_page'] = _page(root, 'Viral-Radar (interno)', '📡', [
            notion.para([notion.rt(f'Log of the watcher and staging area: new {OURS} format pages wait here until they '
                                   'pass every check. Not for creators.')])])
    first_lab = None
    for key, m in cfg['markets'].items():
        T = TEXT[m['lang']]
        mp = pages.setdefault('markets', {}).setdefault(key, {})
        if not mp.get('guide'):
            mp['guide'] = _page(root, f"{T['flag']} {T['guide']}", '📘')
            for k in ('list_page', 'holder_page', 'archive_page'):  # older layout: these sat directly under the root
                if mp.get(k):
                    notion.move_page(mp[k], mp['guide'])
            lab_id = (mp.get('visual_hook_lab') or '').rstrip('/').split('/')[-1].split('-')[-1]
            if lab_id and lab_id.replace('-', '') not in {(x.get('visual_hook_lab') or '').split('/')[-1]
                                                         for k2, x in pages['markets'].items() if k2 != key}:
                notion.move_page(lab_id, mp['guide'])
        guide = mp['guide']
        if not mp.get('visual_hook_lab'):
            other = next((x['visual_hook_lab'] for x in pages['markets'].values() if x.get('visual_hook_lab')), None)
            if other:  # until this market's own (translated) lab exists - see hook_lab
                mp['visual_hook_lab'] = other
            else:
                lab = _page(guide, 'Visual Hook Lab', '🎬', [
                    notion.block('heading_2', [notion.rt('Ideje za prve 3 sekunde')]),
                    *[notion.block('bulleted_list_item', [notion.rt(x)]) for x in HOOK_IDEAS]])
                mp['visual_hook_lab'] = f"https://app.notion.com/p/{lab.replace('-', '')}"
        if not mp.get('holder_page'):
            mp['holder_page'] = _page(guide, T['holder'], '🗂️')
        if not mp.get('archive_page'):
            mp['archive_page'] = _page(guide, T['archive'], '📦')
        if not mp.get('list_page'):
            lab = mp['visual_hook_lab'].rstrip('/').split('/')[-1].split('-')[-1]
            mp['list_page'] = _page(guide, T['list_title'], '👉', list_blocks(T, lab, mp['holder_page'], viral))
        state.save('notion.json', pages)
    print('setup-notion:', pages)
    return pages


# The Parakeet AI Visual Hook Lab (copied into this workspace with its videos) in Serbo-Croatian: the same page,
# block by block - only the words change. Keys are the German text without ** and spaces.
HOOK_LAB_SH = {
    'Warum du Visual Hooks nutzen solltest ⁉️': 'Zašto da koristiš visual hookove ⁉️',
    'Visual Hooks = mehr Aufmerksamkeit = mehr Views = mehr Geld.':
        '**Visual hookovi = više pažnje = više pregleda = više novca.**',
    'Rede also nicht einfach nur in die Kamera – gib den Leuten einen Grund weiterzuschauen. 🔥':
        'Zato nemoj samo pričati u kameru – daj ljudima razlog da gledaju dalje. 🔥',
    'Das Visual-Hook-Rezept 🧪': 'Recept za visual hook 🧪',
    'Du willst einen Visual Hook, der die Leute wirklich am Schauen hält? Nutze diese Formel:':
        'Želiš visual hook koji ljude stvarno drži da gledaju? Koristi ovu formulu:',
    '⚡ Sofort loslegen': '**⚡ Kreni odmah**',
    'Die Action sollte schon ab dem ersten Frame laufen.': 'Radnja mora teći već od prvog kadra.',
    '🔄 In Bewegung bleiben': '**🔄 Ostani u pokretu**',
    'Wähle etwas, das du natürlich weitermachen kannst, während du die Story erzählst.':
        'Izaberi nešto što možeš prirodno nastaviti dok pričaš priču.',
    '📈 Fortschritt zeigen': '**📈 Pokaži napredak**',
    'Anfang → Prozess → fertiges Ergebnis. Gib den Zuschauern etwas, das sie zu Ende sehen wollen 👀':
        'Početak → proces → gotov rezultat. Daj ljudima nešto što žele vidjeti do kraja 👀',
    '🎯 Halte es mühelos': '**🎯 Neka izgleda lako**',
    'Du solltest weiterhin in die Kamera schauen, natürlich sprechen und die Story selbstbewusst erzählen können.':
        'I dalje moraš moći gledati u kameru, prirodno pričati i samouvjereno ispričati priču.',
    'Die perfekte Mischung:': 'Savršena kombinacija:',
    'Sofortige Action + durchgehende Bewegung + sichtbarer Fortschritt + natürliche Präsentation = 🔥':
        'Radnja odmah + stalni pokret + vidljiv napredak + prirodan nastup = 🔥',
    'Hook-Experimente 🎲': 'Eksperimenti s hookovima 🎲',
    'Mit Visual Hooks solltest du immer weiter experimentieren – nicht einmal einstellen und vergessen. Verlass dich nicht jedes Mal auf denselben Hook.':
        'S visual hookovima **stalno isprobavaj nešto novo – nemoj jednom namjestiti pa zaboraviti**. Nemoj se svaki '
        'put oslanjati na isti hook.',
    'Probiere verschiedene Aktionen aus. Wechsle die Objekte. Ändere das Setup. Mach es schräger, simpler, befriedigender oder überraschender.':
        'Probaj različite radnje. Mijenjaj predmete. Promijeni postavku. Napravi ga čudnijim, jednostavnijim, ugodnijim '
        'za gledanje ili iznenađujućim.',
    'Je mehr du testest, desto schneller verstehst du, was bei deiner Audience funktioniert.':
        'Što više testiraš, brže ćeš shvatiti koji hook prolazi kod tvoje publike.',
    'Formate, die du priorisieren solltest 🔝': 'Formati koji imaju prednost 🔝',
    'Befriedigende Transformationen — Schälen, mischen, bauen, zerdrücken, auspressen oder etwas mit klarem Vorher-Nachher verändern.':
        '**Transformacije koje je ugodno gledati** — guljenje, miješanje, slaganje, gnječenje, cijeđenje ili mijenjanje '
        'nečega s jasnim prije-poslije.',
    'Haptische Texturen — Nutze Slime, Knete, Squishies, Essen oder alles Griffige, das sich gut anfühlt und befriedigend anzusehen ist.':
        '**Teksture koje želiš dodirnuti** — slime, plastelin, squishy igračke, hrana ili bilo koja stvar koja je ugodna '
        'na dodir i lijepa za gledanje.',
    'Unerwartete Aktionen — Mach etwas leicht Schräges, Überraschendes oder „Falsches“, das die Zuschauer stoppen und hinschauen lässt.':
        '**Neočekivane radnje** — napravi nešto malo čudno, iznenađujuće ili „pogrešno“ zbog čega ljudi stanu i '
        'pogledaju.',
    'Bauen, sortieren & anordnen — Staple, ordne, verbinde, trenne oder erstelle Muster mit kleinen Objekten.':
        '**Slaganje, sortiranje i raspoređivanje** — slaži, poredaj, spajaj, razdvajaj ili pravi uzorke od sitnih '
        'predmeta.',
    'Beispiele:': 'Primjeri:',
    'Mit dem Tacker spielen 🎒': 'Igranje s heftalicom (klamericom) 🎒',
    'Mit Slime spielen 🍦': 'Igranje sa slimeom 🍦',
    'Ein Getränk aufschäumen oder durchgehend umrühren 🍹': 'Pjenjenje pića ili stalno miješanje 🍹',
    'Langsam ein Stück Obst schälen 🍌': 'Polako guljenje voća 🍌',
    'Ein Lebensmittel mit der Schere zerschneiden 🥒': 'Rezanje hrane makazama (škarama) 🥒',
    'Einen Snack in immer kleinere Stücke brechen 🍫': 'Lomljenje grickalice na sve manje komade 🍫',
    'Falschgeld zerschneiden 💶': 'Rezanje lažnog novca 💶',
    'Wasser zwischen Behältern hin- und hergießen 🪣': 'Presipanje vode iz posude u posudu 🪣',
    'Eine Orange mit der Hand auspressen 🍊': 'Cijeđenje narandže rukom 🍊',
    'Zahnpasta auf die falsche Seite der Zahnbürste geben 🦷': 'Pasta za zube na pogrešnu stranu četkice 🦷',
    'Könntest du das nächste Beispiel liefern? 🤯': 'Možeš li ti biti sljedeći primjer? 🤯',
    'Probier eins aus, mach es zu deinem eigenen und teste, wie es performt. Wenn es gut läuft, kannst du dir einen Platz auf dieser Anleitungsseite als Beispiel für andere Creator sichern. 🔥':
        'Probaj jedan, prilagodi ga sebi i testiraj kako prolazi. Ako dobro prođe, **možeš dobiti mjesto na ovoj '
        'stranici kao primjer za druge kreatore. 🔥**',
    'Zerdrücke Cornflakes mit der Hand auf dem Tisch 🥣': 'Zdrobi kukuruzne pahuljice rukom na stolu 🥣',
    'Gieße Soße direkt auf den Tisch und tunke Chips hinein 🌶️': 'Izlij umak direktno na stol i umači čips 🌶️',
    'Papier immer wieder zerknüllen und glattstreichen 📄': 'Gužvaj papir pa ga opet izravnaj, iznova 📄',
    'Büroklammern zu einer langen Kette verbinden 📎': 'Spajaj spajalice u dugi lanac 📎',
    'Ein Stück Obst von außen abbürsten 🍎🪥': 'Četkom očisti voće izvana 🍎🪥',
    'Einen Keks als Geschenk einpacken 🍪🎁': 'Upakuj keks kao poklon 🍪🎁',
    'Süßigkeiten mit einer Pinzette aufheben und sortieren 🍬🔬': 'Pincetom pokupi i sortiraj slatkiše 🍬🔬',
    'Sticker oder Pflaster auf Obst kleben 🍓🩹': 'Lijepi naljepnice ili flastere na voće 🍓🩹',
}


HOOK_LAB_SL = {
    'Warum du Visual Hooks nutzen solltest ⁉️': 'Zakaj naj uporabljaš vizualne hooke ⁉️',
    'Visual Hooks = mehr Aufmerksamkeit = mehr Views = mehr Geld.':
        '**Vizualni hooki = več pozornosti = več ogledov = več denarja.**',
    'Rede also nicht einfach nur in die Kamera – gib den Leuten einen Grund weiterzuschauen. 🔥':
        'Zato ne govori samo v kamero – daj ljudem razlog, da gledajo naprej. 🔥',
    'Das Visual-Hook-Rezept 🧪': 'Recept za vizualni hook 🧪',
    'Du willst einen Visual Hook, der die Leute wirklich am Schauen hält? Nutze diese Formel:':
        'Želiš vizualni hook, ob katerem ljudje res gledajo naprej? Uporabi to formulo:',
    '⚡ Sofort loslegen': '**⚡ Začni takoj**',
    'Die Action sollte schon ab dem ersten Frame laufen.': 'Dogajanje naj teče že od prve sličice.',
    '🔄 In Bewegung bleiben': '**🔄 Ostani v gibanju**',
    'Wähle etwas, das du natürlich weitermachen kannst, während du die Story erzählst.':
        'Izberi nekaj, kar lahko naravno nadaljuješ, medtem ko pripoveduješ zgodbo.',
    '📈 Fortschritt zeigen': '**📈 Pokaži napredek**',
    'Anfang → Prozess → fertiges Ergebnis. Gib den Zuschauern etwas, das sie zu Ende sehen wollen 👀':
        'Začetek → postopek → končni rezultat. Daj ljudem nekaj, kar želijo videti do konca 👀',
    '🎯 Halte es mühelos': '**🎯 Naj bo videti lahkotno**',
    'Du solltest weiterhin in die Kamera schauen, natürlich sprechen und die Story selbstbewusst erzählen können.':
        'Še vedno moraš lahko gledati v kamero, naravno govoriti in samozavestno povedati zgodbo.',
    'Die perfekte Mischung:': 'Popolna kombinacija:',
    'Sofortige Action + durchgehende Bewegung + sichtbarer Fortschritt + natürliche Präsentation = 🔥':
        'Takojšnje dogajanje + stalno gibanje + viden napredek + naraven nastop = 🔥',
    'Hook-Experimente 🎲': 'Eksperimenti s hooki 🎲',
    'Mit Visual Hooks solltest du immer weiter experimentieren – nicht einmal einstellen und vergessen. Verlass dich nicht jedes Mal auf denselben Hook.':
        'Z vizualnimi hooki **ves čas preizkušaj kaj novega – ne nastavi enkrat in pozabi**. Ne zanašaj se vsakič na '
        'isti hook.',
    'Probiere verschiedene Aktionen aus. Wechsle die Objekte. Ändere das Setup. Mach es schräger, simpler, befriedigender oder überraschender.':
        'Preizkusi različna dejanja. Menjaj predmete. Spremeni postavitev. Naj bo bolj čudno, preprostejše, prijetnejše '
        'za gledanje ali bolj presenetljivo.',
    'Je mehr du testest, desto schneller verstehst du, was bei deiner Audience funktioniert.':
        'Več ko testiraš, hitreje ugotoviš, kaj deluje pri tvojem občinstvu.',
    'Formate, die du priorisieren solltest 🔝': 'Formati, ki imajo prednost 🔝',
    'Befriedigende Transformationen — Schälen, mischen, bauen, zerdrücken, auspressen oder etwas mit klarem Vorher-Nachher verändern.':
        '**Transformacije, ki jih je prijetno gledati** — lupljenje, mešanje, sestavljanje, mečkanje, ožemanje ali '
        'spreminjanje nečesa z jasnim prej-potem.',
    'Haptische Texturen — Nutze Slime, Knete, Squishies, Essen oder alles Griffige, das sich gut anfühlt und befriedigend anzusehen ist.':
        '**Teksture, ki se jih želiš dotakniti** — slime, plastelin, squishy igrače, hrana ali karkoli, kar je prijetno '
        'na otip in lepo za gledanje.',
    'Unerwartete Aktionen — Mach etwas leicht Schräges, Überraschendes oder „Falsches“, das die Zuschauer stoppen und hinschauen lässt.':
        '**Nepričakovana dejanja** — naredi nekaj rahlo čudnega, presenetljivega ali »napačnega«, zaradi česar se ljudje '
        'ustavijo in pogledajo.',
    'Bauen, sortieren & anordnen — Staple, ordne, verbinde, trenne oder erstelle Muster mit kleinen Objekten.':
        '**Sestavljanje, razvrščanje in urejanje** — zlagaj, razvrščaj, povezuj, ločuj ali delaj vzorce iz majhnih '
        'predmetov.',
    'Beispiele:': 'Primeri:',
    'Mit dem Tacker spielen 🎒': 'Igranje s spenjačem 🎒',
    'Mit Slime spielen 🍦': 'Igranje s slimom 🍦',
    'Ein Getränk aufschäumen oder durchgehend umrühren 🍹': 'Penjenje pijače ali nenehno mešanje 🍹',
    'Langsam ein Stück Obst schälen 🍌': 'Počasno lupljenje sadja 🍌',
    'Ein Lebensmittel mit der Schere zerschneiden 🥒': 'Rezanje hrane s škarjami 🥒',
    'Einen Snack in immer kleinere Stücke brechen 🍫': 'Lomljenje prigrizka na vedno manjše koščke 🍫',
    'Falschgeld zerschneiden 💶': 'Rezanje lažnega denarja 💶',
    'Wasser zwischen Behältern hin- und hergießen 🪣': 'Prelivanje vode iz posode v posodo 🪣',
    'Eine Orange mit der Hand auspressen 🍊': 'Ožemanje pomaranče z roko 🍊',
    'Zahnpasta auf die falsche Seite der Zahnbürste geben 🦷': 'Zobna pasta na napačno stran zobne ščetke 🦷',
    'Könntest du das nächste Beispiel liefern? 🤯': 'Si lahko ti naslednji primer? 🤯',
    'Probier eins aus, mach es zu deinem eigenen und teste, wie es performt. Wenn es gut läuft, kannst du dir einen Platz auf dieser Anleitungsseite als Beispiel für andere Creator sichern. 🔥':
        'Preizkusi enega, prilagodi ga sebi in testiraj, kako se obnese. Če se dobro obnese, **si lahko prislužiš mesto '
        'na tej strani kot primer za druge ustvarjalce. 🔥**',
    'Zerdrücke Cornflakes mit der Hand auf dem Tisch 🥣': 'Z roko zdrobi koruzne kosmiče na mizi 🥣',
    'Gieße Soße direkt auf den Tisch und tunke Chips hinein 🌶️': 'Polij omako naravnost na mizo in vanjo pomakaj čips 🌶️',
    'Papier immer wieder zerknüllen und glattstreichen 📄': 'Papir vedno znova zmečkaj in zgladi 📄',
    'Büroklammern zu einer langen Kette verbinden 📎': 'Sponke za papir spenjaj v dolgo verigo 📎',
    'Ein Stück Obst von außen abbürsten 🍎🪥': 'S ščetko od zunaj očisti kos sadja 🍎🪥',
    'Einen Keks als Geschenk einpacken 🍪🎁': 'Zavij piškot kot darilo 🍪🎁',
    'Süßigkeiten mit einer Pinzette aufheben und sortieren 🍬🔬': 'S pinceto pobiraj in razvrščaj sladkarije 🍬🔬',
    'Sticker oder Pflaster auf Obst kleben 🍓🩹': 'Lepi nalepke ali obliže na sadje 🍓🩹',
}


def _key(text):
    return ''.join((text or '').replace('**', '').split())


def _walk(block_id):
    for b in notion.children(block_id):
        yield b
        if b.get('has_children') and b['type'] not in ('child_page', 'child_database'):
            yield from _walk(b['id'])


TABLES = {'sh': HOOK_LAB_SH, 'sl': HOOK_LAB_SL}
KEEP = ('rich_text', 'color', 'icon', 'is_toggleable', 'caption', 'language', 'checked')


def _rich(rich):
    out = []
    for x in rich or []:
        if x.get('type') == 'mention':
            out.append({'type': 'mention', 'mention': x['mention'], 'annotations': x.get('annotations', {})})
        else:
            out.append({'type': 'text', 'text': {'content': x.get('plain_text', ''), 'link': (x.get('text') or {}).get('link')},
                        'annotations': x.get('annotations', {})})
    return out


def _clone(b, work):
    """A block ready to be created again (Notion-hosted videos/images are downloaded and uploaded again)."""
    import requests
    t = b['type']
    data = b.get(t) or {}
    if t in ('video', 'image', 'file'):
        src = (data.get('file') or {}).get('url') or (data.get('external') or {}).get('url')
        if data.get('type') == 'external':
            return {'object': 'block', 'type': t, t: {'type': 'external', 'external': data['external']}}
        path = os.path.join(work, f"{b['id']}.mp4" if t == 'video' else b['id'])
        with requests.get(src, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
        if t == 'video':
            from . import media
            path = media.for_notion(path, work)
        return {'object': 'block', 'type': t, t: {'type': 'file_upload', 'file_upload': {'id': notion.upload_video(path)}}}
    body = {k: (_rich(v) if k in ('rich_text', 'caption') else v) for k, v in data.items() if k in KEEP and v is not None}
    return {'object': 'block', 'type': t, t: body}


def _copy_children(src, dst, work):
    """Copies every block below src to dst, level by level (the API takes at most two levels per request)."""
    for b in notion.children(src):
        if b['type'] in ('child_page', 'child_database', 'unsupported'):
            continue
        new = _clone(b, work)
        if b['type'] == 'column_list':  # a column list must be created together with its columns and their content
            cols = []
            for col in notion.children(b['id']):
                cols.append({'object': 'block', 'type': 'column', 'column': {**({'width_ratio': col['column']['width_ratio']}
                             if (col.get('column') or {}).get('width_ratio') else {})},
                             'children': [_clone(c, work) for c in notion.children(col['id'])]})
            new['column_list'] = {'children': cols}
            notion.api('PATCH', f'/blocks/{dst}/children', {'children': [new]})
            continue
        made = notion.api('PATCH', f'/blocks/{dst}/children', {'children': [new]})['results'][0]
        if b.get('has_children'):
            _copy_children(b['id'], made['id'], work)


def copy_page(src, parent, title, icon, into=None):
    """Copies the page src (blocks + uploaded videos) to a new page under parent - or into the page `into` (an earlier
    copy that stopped halfway: its blocks are replaced, the page itself is kept)."""
    import shutil
    import tempfile
    work = tempfile.mkdtemp(prefix='copy-')
    try:
        if into:
            for b in notion.children(into):
                if b['type'] not in ('child_page', 'child_database'):
                    notion.api('DELETE', f"/blocks/{b['id']}")
            page_id = into
        else:
            page_id = notion.create_page(parent, title, icon, [])['id']
        _copy_children(src, page_id, work)
        return page_id
    finally:
        shutil.rmtree(work, ignore_errors=True)


def hook_lab(cfg, market=None, page=None):
    """A copy of the Parakeet Visual Hook Lab (videos included) -> this market's language, moved into the market's
    guide page, then it becomes the lab every page of that market links to (state/notion.json + the 🚨 rule).
    The copy may be the German original or another market's translation; only the words change."""
    pages = state.load('notion.json', {})
    market = market or next(iter(cfg['markets']))
    mp = pages['markets'][market]
    lang = cfg['markets'][market]['lang']
    lab = page or next(
        (b['id'] for b in notion.children(pages['root']) if b['type'] == 'child_page' and 'Visual Hook Lab' in b['child_page']['title']
         and (notion.api('GET', f"/pages/{b['id']}").get('icon') or {}).get('emoji') == '👀'), None)
    others = {x.get('visual_hook_lab') for k, x in pages['markets'].items() if k != market}
    if (not lab or (not page and mp.get('visual_hook_lab') in others)) and others - {None, ''}:
        # no copy of its own yet: copy another market's lab (videos included) into this market's guide page
        source = sorted(others - {None, ''})[0].rstrip('/').split('/')[-1].split('-')[-1]
        parent = mp.get('guide') or pages['root']
        earlier = next((b['id'] for b in notion.children(parent) if b['type'] == 'child_page'
                        and b['child_page']['title'] == 'Visual Hook Lab'), None)  # a copy that stopped halfway
        lab = copy_page(source, parent, 'Visual Hook Lab', '👀', into=earlier)
        print('hook-lab: copied', source, '->', lab)
    if not lab:
        raise SystemExit('hook-lab: no 👀 Visual Hook Lab copy found')
    target = TABLES[lang]
    table = {}
    for de, value in target.items():  # match the German text and every other language's version of it
        table[_key(de)] = value
        for other in TABLES.values():
            if de in other:
                table[_key(other[de])] = value
    done, left = 0, []
    for b in _walk(lab):
        rich = (b.get(b['type']) or {}).get('rich_text')
        if not rich:
            continue
        text = ''.join(x.get('plain_text', '') for x in rich)
        new = table.get(_key(text))
        if new is None:
            if any(c.isalpha() for c in text):
                left.append(text[:80])
            continue
        if _key(new) != _key(text):
            notion.api('PATCH', f"/blocks/{b['id']}", {b['type']: {'rich_text': notion.md(new)}})
        done += 1
    notion.api('PATCH', f'/pages/{lab}', {'icon': {'type': 'emoji', 'emoji': '👀'},
                                          'properties': {'title': {'title': [notion.rt('Visual Hook Lab')]}}})
    if mp.get('guide'):
        parent = (notion.api('GET', f'/pages/{lab}').get('parent') or {}).get('page_id', '')
        if parent.replace('-', '') != mp['guide'].replace('-', ''):
            notion.move_page(lab, mp['guide'])
    url = f"https://app.notion.com/p/{lab.replace('-', '')}"
    mp['visual_hook_lab'] = url
    T = TEXT[lang]
    for b in notion.children(mp['list_page']) if mp.get('list_page') else []:
        if b['type'] == 'callout' and ((b['callout'].get('icon') or {}).get('emoji') == '🚨'):
            notion.api('PATCH', f"/blocks/{b['id']}", {'callout': {'rich_text': notion.md(T['visual_rule'])
                                                                               + [notion.mention(lab), notion.rt('.')]}})
    state.save('notion.json', pages)
    print(f'hook-lab {market}: {done} blocks in {T["lang_name"]}; not matched: {left or "none"}; lab = {url}')


def relink(cfg, fmts, page_of):
    """Every format page (live, held or archived): app links and their labels point to the current app link
    (config links.memo). Only links change - no text, no layout."""
    from .brand import CUE_LABEL, OURS_SITE
    target = cfg['links']['memo']
    changed = 0
    for f in fmts:
        for key in cfg['markets']:
            pid = page_of(f, key)
            for b in _walk(pid) if pid else []:
                rich = (b.get(b['type']) or {}).get('rich_text')
                if not rich:
                    continue
                new, touched = [], False
                for x in rich:
                    link = ((x.get('text') or {}).get('link') or {}).get('url', '')
                    if x.get('type') == 'text' and OURS_SITE in link and link != target:
                        label = x['plain_text']
                        if label.startswith('Memo AI ·'):
                            label = CUE_LABEL
                        x = {'type': 'text', 'text': {'content': label, 'link': {'url': target}},
                             'annotations': x.get('annotations', {})}
                        touched = True
                    elif x.get('type') == 'text':
                        x = {'type': 'text', 'text': {'content': x['plain_text'], 'link': (x.get('text') or {}).get('link')},
                             'annotations': x.get('annotations', {})}
                    elif x.get('type') == 'mention':
                        x = {'type': 'mention', 'mention': x['mention'], 'annotations': x.get('annotations', {})}
                    new.append(x)
                if touched:
                    notion.api('PATCH', f"/blocks/{b['id']}", {b['type']: {'rich_text': new}})
                    changed += 1
    print(f'relink: {changed} blocks now link to {target}')
