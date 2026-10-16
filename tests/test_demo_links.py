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
