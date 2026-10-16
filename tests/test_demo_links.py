"""Creators play a ready-made Memo AI demo recording and film the screen (user's decision, 16 Oct 2026): the cue
and the materials box point to the recordings; a format with its own app page (the oral quiz) keeps that page."""
from unittest import mock

from watcher import brand, notion
from watcher.markets import TEXT

FOLDER = 'https://drive.google.com/drive/folders/DEMO'
VIDEOS = {'mac': 'https://drive.google.com/file/d/MAC/view', 'windows': 'https://drive.google.com/file/d/WIN/view',
          'iphone': 'https://drive.google.com/file/d/IPH/view', 'android': 'https://drive.google.com/file/d/AND/view'}
QUIZ = 'https://www.memoai.eu/ugc/oral-quiz'


def test_cue_says_play_the_demo():
    assert brand.is_demo_link(FOLDER) and not brand.is_demo_link(QUIZ)
    assert notion.cue_label_for(FOLDER, 'sh') == '🎥 Ovdje pusti Memo AI demo'
    assert notion.cue_label_for(FOLDER, 'sh', first=False) == '🎥 Memo AI demo'
    assert notion.cue_label_for(FOLDER, 'sl') == '🎥 Tukaj predvajaj Memo AI demo'
    assert notion.cue_label_for(QUIZ, 'sl') == '🎥 Posnemi Memo AI · memoai.eu/ugc/oral-quiz'  # the oral quiz keeps its page


def test_materials_link_each_device():
    with mock.patch.object(notion, 'demo_videos', lambda lang: VIDEOS):
        rich = notion.record_rule_rich('sl', FOLDER)
    links = {x['text']['content']: (x['text'].get('link') or {}).get('url') for x in rich}
    assert links['Mac'] == VIDEOS['mac'] and links['Windows'] == VIDEOS['windows']
    assert links['iPhone'] == VIDEOS['iphone'] and links['Android'] == VIDEOS['android']
    plain = ''.join(x['text']['content'] for x in rich)
    assert plain == ' – ' + notion.record_rule_text('sl', FOLDER)
    assert 'Mac · Windows · iPhone · Android' in plain and 'memoai.eu' not in plain
    assert notion.record_rule_text('sh', QUIZ) == TEXT['sh']['record_rule_app']


def test_page_has_no_creator_link():
    spec = {'title_hook': 'X', 'script': [{'cue': 'memo', 'asset_name': '', 'text': 'Tole je Memo AI.', 'new_paragraph': True}],
            'visual_hook': 'Y', 'assets_needed': []}
    with mock.patch.object(notion, 'demo_videos', lambda lang: VIDEOS), mock.patch.object(notion.builder, 'hook_lines', lambda s, l: ['Y']):
        blocks = notion.page_blocks(spec, {'url': 'https://www.tiktok.com/@a/video/1'}, None, {'memo': FOLDER}, lang='sh')
    urls, text = [], ''
    for b in blocks:
        for x in (b.get(b['type']) or {}).get('rich_text', []):
            text += x['text']['content'] if x.get('type') == 'text' else ''
            urls.append(((x.get('text') or {}).get('link') or {}).get('url'))
    assert 'memoai.eu/creator' not in text and not any(u and 'memoai.eu' in u for u in urls)
    assert FOLDER in urls and all(v in urls for v in VIDEOS.values())
    note = '\n'.join(notion.inspo_note('sh'))
    assert 'preuzmi' in note and 'overlay' in note and 'Android snimak' in note and 'memoai.eu/creator' not in note


def test_one_demo_cue_right_after_the_app_is_named():
    spec = {'script': [{'cue': None, 'asset_name': '', 'text': 'Prvi stavek.', 'new_paragraph': True},
                       {'cue': 'memo', 'asset_name': '', 'text': 'Rekla mi je: »Odpri Memo AI.« Vanjo naložiš PDF-je.', 'new_paragraph': True},
                       {'cue': 'memo', 'asset_name': '', 'text': 'In dobiš kartice.', 'new_paragraph': False}]}
    paras = [''.join(x['text']['content'] for x in p['paragraph']['rich_text']) for p in notion.script_paragraphs(spec, {'memo': FOLDER}, 'sl')]
    assert paras[1] == 'Rekla mi je: »Odpri Memo AI.« (🎥 Tukaj predvajaj Memo AI demo) Vanjo naložiš PDF-je. In dobiš kartice. '
    # the oral quiz's own page keeps its cues
    quiz = notion.script_paragraphs(spec, {'memo': QUIZ}, 'sl')
    assert sum('🎥' in x['text']['content'] for p in quiz for x in p['paragraph']['rich_text']) == 2


def test_live_page_keeps_one_cue_after_the_name():
    from watcher import democue
    it = lambda t, link=None: {'type': 'text', 'plain_text': t, 'text': {'content': t, 'link': {'url': link} if link else None}, 'annotations': {}}
    blocks = [{'id': 'a', 'type': 'paragraph', 'paragraph': {'rich_text': [
        it('('), it('🎥 Tukaj predvajaj Memo AI demo', FOLDER), it(') Druga, ki sem jo največ uporabljala, je Memo AI. ('),
        it('🎥 Memo AI demo', FOLDER), it(') Vanjo naložiš PDF-je.')]}}]
    out = democue.fix_page(blocks, 'sl')
    assert ''.join(x['text']['content'] for x in out['a']) == \
        'Druga, ki sem jo največ uporabljala, je Memo AI. (🎥 Tukaj predvajaj Memo AI demo) Vanjo naložiš PDF-je.'
    assert democue.fix_page([{'id': 'b', 'type': 'paragraph', 'paragraph': {'rich_text': out['a']}}], 'sl') == {}  # stable
    assert democue.anchor('Memo AI: Tvoja pacientka …') is None  # a speaker label is not the creator naming the app


def test_cue_after_the_name_in_spoken_lines():
    from watcher import democue
    cut = lambda t: t[:democue.anchor(t, 'Tekst na ekranu:')]
    assert cut('Ako koristiš Memo AI aplikaciju za učenje, ispadaš, jer je realno najbolja aplikacija za učenje i time već pobjeđuješ.') \
        == 'Ako koristiš Memo AI aplikaciju za učenje,'
    assert cut('One koriste ovu aplikaciju, Memo AI, i ti ovdje samo ubaciš svoje bilješke – a ako ih nemaš, uslikaš tuđe.') \
        == 'One koriste ovu aplikaciju, Memo AI,'
    assert cut('Ubacim PDF-ove, a mogu i snimiti predavanje i taj audio snimak ubaciti u Memo AI – dobijem bilješke, flash kartice, testove, kvizove i još mnogo drugih funkcija.') \
        == 'Ubacim PDF-ove, a mogu i snimiti predavanje i taj audio snimak ubaciti u Memo AI'
    assert democue.anchor('Tekst na ekranu: 3/4 Memo AI 🧠', 'Tekst na ekranu:') is None


def test_cue_moves_from_an_on_screen_line_to_where_the_name_is_said():
    from watcher import democue
    seg = lambda text, cue=None, new=True: {'cue': cue, 'asset_name': '', 'text': text, 'new_paragraph': new}
    popusti = [seg('Kao drugo, besplatan Microsoft Office.'), seg('Tekst na ekranu: 3/4 Memo AI 🧠', 'memo'),
               seg('Kao treće, na Memo AI imate besplatan trial: u tu aplikaciju ubacite PDF-ove.'), seg('Komentariši »POPUST«.')]
    out = democue.fix_spec(popusti, 'sh')
    assert [(s['text'], s['cue']) for s in out[1:4]] == [
        ('Tekst na ekranu: 3/4 Memo AI 🧠', None), ('Kao treće, na Memo AI imate besplatan trial:', None),
        ('u tu aplikaciju ubacite PDF-ove.', 'memo')]
    mozak = [seg('POV: nisi pretplaćen na mozak premium', 'asset'), seg('Pa highkey nadogradiš mozak uz Memo AI', 'memo'),
             seg('PDF, PowerPoint ili snimak predavanja → bilješke, kartice i kvizovi 🧠')]
    assert [s['cue'] for s in democue.fix_spec(mozak, 'sh')] == ['asset', None, 'memo']  # the name ends the line: next line


def test_old_wording_comes_back_and_the_cue_stays_after_the_name():
    from watcher import democue
    it = lambda t, link=None: {'type': 'text', 'plain_text': t, 'text': {'content': t, 'link': {'url': link} if link else None}, 'annotations': {}}
    rich = [it('Druga je Memo AI. ('), it('🎥 Tukaj predvajaj Memo AI demo', FOLDER),
            it(') Vanjo naložiš PDF-je ali posnameš predavanje in dobiš urejene zapiske, kvize in miselni vzorec. '), it('Na primer kviz.')]
    now = 'Druga je Memo AI. Vanjo naložiš PDF-je ali posnameš predavanje in dobiš urejene zapiske, kvize in miselni vzorec. Na primer kviz.'
    old = 'Druga je Memo AI. Vanjo naložiš PDF-je, lahko pa predavanje tudi posnameš. Ven dobiš zapiske, teste in kvize. Na primer kviz.'
    assert democue.restore(rich, 'nekaj drugega', old) is None
    back = democue.restore(rich, now, old)
    plain = lambda r: ''.join(x['text']['content'] for x in r)
    assert plain(back) == '(🎥 Tukaj predvajaj Memo AI demo) ' + old
    block = [{'id': 'a', 'type': 'paragraph', 'paragraph': {'rich_text': [dict(x, plain_text=x['text']['content']) for x in back]}}]
    assert plain(democue.fix_page(block, 'sl')['a']) == \
        'Druga je Memo AI. (🎥 Tukaj predvajaj Memo AI demo) Vanjo naložiš PDF-je, lahko pa predavanje tudi posnameš. Ven dobiš zapiske, teste in kvize. Na primer kviz.'
    assert democue.reads('Druga je Memo AI. (🎥 Tukaj predvajaj Memo AI demo) Vanjo', 'Druga je Memo AI. Vanjo')
