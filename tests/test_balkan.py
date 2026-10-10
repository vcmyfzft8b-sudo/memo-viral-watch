"""The Astra AI -> Memo AI / Balkan specifics: brand counting, language checks, region filter, Slack DM."""
from unittest import mock

from watcher import brand, builder, discover, markets, notify


def test_brand_counts_spoken_forms_and_mishearings():
    assert brand.count_source('Astra AI je super, astraai, astra.ai, Astra A.I.') == 4
    assert brand.count_source('pilastra i alabastra') == 0
    assert brand.count_source('besplatni trial na ASTRI AI, uz Astru, s Astrom, z Astro, od Astre') == 5
    assert brand.count_source('astronomija, astrologija, Astrid') == 0
    assert brand.count_source('Ovo polje je kupio Studyflash. Study Flash pomaže.') == 2  # hand-added format's app
    assert not brand.says_watched('Studyflash') and brand.says_watched('Astra AI')  # creators: Astra AI only
    assert 'Studyflash' in brand.FACTS
    assert brand.count_ours('Probaj Memo AI na memoai.eu') == 2
    assert brand.count_ours('memo za sutra') == 0


def test_market_language_names_and_codes():
    for x in ('Croatian', 'Serbian', 'Bosnian', 'Montenegrin', 'Serbo-Croatian', 'hr', 'sr', 'bs'):
        assert markets.lang_matches('sh', x), x
    for x in ('Slovenian', 'sl', 'German', '', None):
        assert not markets.lang_matches('sh', x), x


def test_ekavian_words_are_found_ijekavian_pass():
    assert markets.avoid_found('sh', 'Uvek imam vreme gde god da sam') == ['gde', 'uvek', 'vreme']
    assert markets.avoid_found('sh', 'Uvijek imam vremena gdje god da sam') == []


def spec(text):
    return {'page_title': 'Naslov 📚', 'title_hook': 'Naslov', 'visual_hook_first': 'Govori u kameru.',
            'voiceover': True, 'script': [{'cue': brand.CUE, 'text': text}]}


def test_validate_blocks_source_brand_cyrillic_and_ekavian():
    ok = 'Sutra je test i ja još nisam ništa naučila, ali Memo AI mi je sve objasnio da sam sve razumjela.'
    assert builder.validate(spec(ok), {'text': ''}) == []
    assert any('Astra AI' in p for p in builder.validate(spec(ok + ' Astra AI'), {'text': ''}))
    assert any('Cyrillic' in p for p in builder.validate(spec(ok + ' и ја'), {'text': ''}))
    assert any('ekavian' in p for p in builder.validate(spec(ok + ' Uvek je lepo.'), {'text': ''}))
    no_app = spec(ok)
    no_app['script'][0]['cue'] = None
    assert any('Memo AI moment' in p for p in builder.validate(no_app, {'text': ''}))


def captions(*texts):
    return [{'id': str(7690000000000000000 + i), 'views': 1, 'desc': t} for i, t in enumerate(texts)]


def test_caption_language_tells_serbo_croatian_from_slovenian():
    with mock.patch.object(discover.tiktok, 'latest_videos', return_value=captions(
            'Ovo je app koji mi je pomogao da naučim sve za test', 'Evo kako učim i što radim kad nemam vremena')):
        assert discover.language('x') == 'sh'
    with mock.patch.object(discover.tiktok, 'latest_videos', return_value=captions(
            'To je aplikacija ki mi je zelo pomagala in je super', 'Kaj delam ko se učim za test, tudi ti lahko')):
        assert discover.language('x') == 'sl'


def test_region_filter_uses_claudes_language_first():
    assert discover.regional('x', {'language': 'Croatian'})
    assert not discover.regional('x', {'language': 'Slovenian'})


def test_slack_goes_to_the_users_direct_messages_when_a_bot_token_is_set():
    env = {'SLACK_BOT_TOKEN': 'xoxb-test', 'SLACK_USER_ID': 'U123', 'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/x'}
    with mock.patch.dict('os.environ', env), mock.patch.object(notify.requests, 'post') as post:
        post.return_value.json.return_value = {'ok': True}
        notify.slack('t', 'm')
    url = post.call_args[0][0]
    assert url == 'https://slack.com/api/chat.postMessage'
    assert post.call_args[1]['json']['channel'] == 'U123'


def test_alerts_go_to_the_discord_channel_in_discord_format():
    with mock.patch.dict('os.environ', {'DISCORD_ALERTS_WEBHOOK_URL': 'https://discord.com/api/webhooks/1/x'}, clear=True), \
            mock.patch.object(notify.requests, 'post') as post:
        post.return_value.status_code = 204
        notify.push('🟢 VIRAL', '@a – *367k views*\n▶ <https://www.tiktok.com/@a/video/1|Open video>')
    body = post.call_args[1]['json']
    assert body['content'] == '**🟢 VIRAL**\n@a – **367k views**\n▶ [Open video](<https://www.tiktok.com/@a/video/1>)'
    assert body['allowed_mentions'] == {'parse': []}


def test_creator_who_only_says_the_app_name_is_found_by_listening():
    import time as _t
    vid = str(int(_t.time()) << 32)
    with mock.patch.object(discover.tiktok, 'latest_videos', return_value=[{'id': vid, 'views': 367000, 'desc': 'Jeste li bolji od 99%?'}]), \
            mock.patch.object(discover.tiktok, 'video_detail', return_value={'desc': '', 'sticker': '', 'subtitles': ''}), \
            mock.patch.dict('os.environ', {'SONIOX_API_KEY': 'k'}), \
            mock.patch('watcher.media.download', return_value='v.mp4'), mock.patch('watcher.media.audio', return_value='a.flac'), \
            mock.patch('watcher.soniox.transcribe', return_value={'text': 'Ako koristiš Astra AI aplikaciju, ispadaš.'}):
        assert discover.check_account('kera.vas.uci') == 'active'
        assert 'Astra AI' in discover.account_text('kera.vas.uci', details=0)
    with mock.patch.object(discover.tiktok, 'latest_videos', return_value=[{'id': vid, 'views': 5, 'desc': 'učimo'}]), \
            mock.patch.object(discover.tiktok, 'video_detail', return_value={'desc': '', 'sticker': '', 'subtitles': ''}), \
            mock.patch.dict('os.environ', {'SONIOX_API_KEY': 'k'}), \
            mock.patch('watcher.media.download', return_value='v.mp4'), mock.patch('watcher.media.audio', return_value='a.flac'), \
            mock.patch('watcher.soniox.transcribe', return_value={'text': 'Danas učimo biologiju.'}):
        assert discover.check_account('someone') == 'inactive'


def test_tracked_creator_is_only_dropped_when_a_second_look_agrees(tmp_path):
    import json as _json
    from watcher import localize, main, state
    accounts = {'kept': {'status': 'active'}, 'dropped': {'status': 'active'}}
    path = tmp_path / 'sync.json'
    path.write_text(_json.dumps({'candidates': []}))
    first = {'kept': {'verdict': 'not_ugc', 'language': 'Serbian'}, 'dropped': {'verdict': 'not_ugc', 'language': 'Serbian'}}
    second = {'kept': {'verdict': 'source_ugc', 'language': 'Serbian'}, 'dropped': {'verdict': 'other_app', 'other_app': 'X'}}
    with mock.patch.object(state, 'DIR', str(tmp_path)), \
            mock.patch.object(discover, 'confirm_ugc', side_effect=[first, second]), \
            mock.patch.object(main, 'backfill', return_value=(0, 0)), mock.patch.object(localize, 'run', return_value=[]), \
            mock.patch.object(main, 'notify'), mock.patch.object(main, 'load_formats', return_value=[]):
        state.save('accounts.json', accounts)
        main.accounts_sync(str(path))
        out = state.load('accounts.json', {})
    assert out['kept']['status'] == 'active' and not out['kept'].get('blocked')
    assert out['dropped']['blocked'] and out['dropped']['status'] == 'inactive'


def test_slovenian_pages_have_every_text_and_reject_serbo_croatian_leftovers():
    assert set(markets.TEXT['sl']) == set(markets.TEXT['sh'])
    ok = 'Jutri pišem test iz biologije in nisem še ničesar odprla, ampak Memo AI mi je vse lepo razložil.'
    assert builder.validate(spec(ok), {'text': ''}, lang='sl') == []
    assert any('Croatian/Serbian' in p for p in builder.validate(spec(ok + ' Što ćeš?'), {'text': ''}, lang='sl'))
    assert any('characters' in p for p in builder.validate(spec(ok + ' Đak.'), {'text': ''}, lang='sl'))
    assert markets.lang_matches('sl', 'Slovenian') and not markets.lang_matches('sl', 'Croatian')


def test_visual_hook_section_is_one_sentence_plus_the_lab_line():
    from watcher import notion
    s = {**spec('Memo AI tekst.'), 'visual_hook_first': 'sjediš za stolom i guliš mandarinu.', 'extra_hook_lines': ['x'],
         'return_to_camera': True}
    assert builder.hook_lines(s, 'sh') == ['Napravi isti vizuelni hook kao u videu za inspiraciju: sjediš za stolom i guliš mandarinu.']
    blocks = notion.page_blocks(s, {'url': 'https://www.tiktok.com/@a/video/1'}, None, {'memo': 'https://memoai.eu/creator'},
                                lang='sh', lab_url='https://lab')
    i = next(k for k, b in enumerate(blocks) if b['type'] == 'heading_2' and '🎬' in b['heading_2']['rich_text'][0]['text']['content'])
    section = blocks[i + 1:next(k for k in range(i + 1, len(blocks)) if blocks[k]['type'] == 'divider')]
    assert len(section) == 2
    assert section[1]['paragraph']['rich_text'][1]['text']['link'] == {'url': 'https://lab'}


def test_reviewers_see_the_visual_hook_lab_line():
    from watcher import notion, reword
    def blk(t, typ='paragraph', link=None):
        x = {'type': 'text', 'plain_text': t, 'text': {'content': t, 'link': {'url': link} if link else None}}
        return {'id': t[:8], 'type': typ, typ: {'rich_text': [x]}}
    page = [blk('🎬 VIZUELNI HOOK', 'heading_2'), blk('Napravi isti vizuelni hook kao u videu za inspiraciju: …'),
            {'id': 'l', 'type': 'paragraph', 'paragraph': {'rich_text': [
                {'type': 'text', 'plain_text': 'Želiš drugi vizuelni hook? Izaberi jedan iz ', 'text': {'content': '', 'link': None}},
                {'type': 'text', 'plain_text': 'Visual Hook Lab', 'text': {'content': '', 'link': {'url': 'https://lab'}}}]}},
            {'id': 'd', 'type': 'divider', 'divider': {}}]
    with mock.patch.object(notion, 'children', lambda pid: page):
        got = [reword._plain(b) for b in reword.direction_blocks('p')]
    assert len(got) == 2 and 'Visual Hook Lab' in got[1]


def test_format_options_markets_link_and_brand_counts():
    from watcher import main
    mkts = [{'key': 'sh'}, {'key': 'sl'}]
    assert markets.of(mkts, {}) == mkts and markets.of(mkts, {'only_markets': ['sl']}) == [{'key': 'sl'}]
    links = {'memo': 'https://memoai.eu/creator'}
    own = brand.links_for(links, {'app_link': 'https://www.memoai.eu/ugc/oral-quiz'})
    assert own['memo'] == 'https://www.memoai.eu/ugc/oral-quiz' and brand.links_for(links, {}) is links
    assert brand.cue_label(own['memo']) == 'Memo AI · memoai.eu/ugc/oral-quiz'
    assert brand.cue_label(links['memo']) == brand.CUE_LABEL
    assert brand.count_app('Probaj Memo AI, koda ŠPELA50') == 1  # an original of our own creators names Memo AI
    assert brand.count_app('Astra AI je super') == 1
    assert brand.count_source('Turbo AI oral quiz') == 1
    with mock.patch.object(main, 'add_format', side_effect=[None, SystemExit('no video')]) as add:
        try:
            main.add_formats('https://a/video/1, https://a/video/2; https://b/video/3')
            raise AssertionError('a failed format must fail the run')
        except SystemExit as e:
            assert 'b/video/3' in str(e)
    assert add.call_args_list[0][0][0] == ['https://a/video/1', ' https://a/video/2']


def test_note_under_the_example_says_other_brand_or_own_video():
    from watcher import audit, notion
    for lang in ('sh', 'sl'):
        other = ' '.join(notion.inspo_note(lang, same_lang=False))
        assert ('drugog brenda' if lang == 'sh' else 'druge znamke') in other and '(vibe)' in other and 'Astra' not in other
        own = ' '.join(notion.inspo_note(lang, same_lang=True, own=True))
        assert 'Memo AI video' in own and 'brenda' not in own and 'znamke' not in own
        for same in (False, True):
            for o in (False, True):
                assert audit._note_is_same(notion.inspo_note(lang, same, o)[0], lang) == same
