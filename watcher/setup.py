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
