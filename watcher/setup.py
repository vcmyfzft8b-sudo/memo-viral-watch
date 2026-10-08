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


def notion_pages(cfg):
    have = state.load('notion.json', {})
    if have.get('radar_page'):
        print('setup-notion: already set up:', have)
        return have
    root = _root()
    viral = hot.views_text(cfg['thresholds']['viral_views'])
    out = {'root': root, 'markets': {}}
    out['radar_page'] = _page(root, 'Viral-Radar (interno)', '📡', [
        notion.para([notion.rt(f'Log of the watcher and staging area: new {OURS} format pages wait here until they pass '
                               'every check. Not for creators.')])])
    for key, m in cfg['markets'].items():
        T = TEXT[m['lang']]
        lab = _page(root, 'Visual Hook Lab', '🎬', [
            notion.block('heading_2', [notion.rt('Ideje za prve 3 sekunde')]),
            *[notion.block('bulleted_list_item', [notion.rt(x)]) for x in HOOK_IDEAS]])
        holder = _page(root, T['holder'], '🗂️')
        archive = _page(root, T['archive'], '📦')
        fire = [notion.rt(T['list_fire'][0]), notion.rt('\n')] + notion.md(T['list_fire'][1].format(views=viral))
        rule = notion.md(T['visual_rule']) + [notion.mention(lab)]
        list_page = _page(root, T['list_heading'], '🔥', [
            notion.block('heading_1', [notion.rt(T['list_heading'])]),
            notion.block('callout', fire, icon={'type': 'emoji', 'emoji': '🔥'}, color='orange_background'),
            notion.block('paragraph', []),
            notion.block('callout', rule, icon={'type': 'emoji', 'emoji': '🚨'}, color='red_background')])
        out['markets'][key] = {'list_page': list_page, 'holder_page': holder, 'archive_page': archive,
                               'visual_hook_lab': f"https://app.notion.com/p/{lab.replace('-', '')}"}
    state.save('notion.json', out)
    print('setup-notion: created', out)
    return out


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


def _key(text):
    return ''.join((text or '').replace('**', '').split())


def _walk(block_id):
    for b in notion.children(block_id):
        yield b
        if b.get('has_children') and b['type'] not in ('child_page', 'child_database'):
            yield from _walk(b['id'])


def hook_lab(cfg):
    """The copied Parakeet Visual Hook Lab (👀, under the main page): text into Serbo-Croatian, then it becomes the
    lab every page links to (state/notion.json + the 🚨 rule on the list). Videos and layout stay as they are."""
    pages = state.load('notion.json', {})
    root = pages.get('root')
    lab = os.environ.get('HOOK_LAB_PAGE') or next(
        (b['id'] for b in notion.children(root) if b['type'] == 'child_page' and 'Visual Hook Lab' in b['child_page']['title']
         and (notion.api('GET', f"/pages/{b['id']}").get('icon') or {}).get('emoji') == '👀'), None)
    if not lab:
        raise SystemExit('hook-lab: no 👀 Visual Hook Lab under the main page')
    table = {_key(k): v for k, v in HOOK_LAB_SH.items()}
    done, left = 0, []
    for b in _walk(lab):
        data = b.get(b['type']) or {}
        rich = data.get('rich_text')
        if not rich:
            continue
        text = ''.join(x.get('plain_text', '') for x in rich)
        new = table.get(_key(text))
        if new is None:
            if any(c.isalpha() for c in text) and _key(text) not in {_key(v) for v in HOOK_LAB_SH.values()}:
                left.append(text[:80])
            continue
        notion.api('PATCH', f"/blocks/{b['id']}", {b['type']: {'rich_text': notion.md(new)}})
        done += 1
    url = f"https://app.notion.com/p/{lab.replace('-', '')}"
    for key in cfg['markets']:
        pages.setdefault('markets', {}).setdefault(key, {})['visual_hook_lab'] = url
        rule_page = pages['markets'][key].get('list_page')
        for b in notion.children(rule_page) if rule_page else []:
            if b['type'] == 'callout' and ((b['callout'].get('icon') or {}).get('emoji') == '🚨'):
                T = TEXT[cfg['markets'][key]['lang']]
                notion.api('PATCH', f"/blocks/{b['id']}", {'callout': {'rich_text': notion.md(T['visual_rule'])
                                                                                    + [notion.mention(lab)]}})
    state.save('notion.json', pages)
    print(f'hook-lab: {done} blocks translated; not translated: {left or "none"}; lab = {url}')
