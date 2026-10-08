"""The Astra AI -> Memo AI / Balkan specifics: brand counting, language checks, region filter, Slack DM."""
from unittest import mock

from watcher import brand, builder, discover, markets, notify


def test_brand_counts_spoken_forms_and_mishearings():
    assert brand.count_source('Astra AI je super, astraai, astra.ai, Astra A.I.') == 4
    assert brand.count_source('pilastra i alabastra') == 0
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
