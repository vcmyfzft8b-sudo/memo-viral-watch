"""Conversion rules (user's rule, 15 Oct 2026): the list holds formats that convert best AND still go viral."""
import json
import os
import tempfile
import time
import unittest
from unittest import mock

from watcher import conversion, detect, hot, lineup, main, rank, state

NOW = 1_800_000_000
DAY = 86400
CFG = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'config.json')))
for _m in CFG['markets'].values():  # the clean-up rules are tested with every market on (sh is stopped in config.json)
    _m['enabled'] = True


def vid(fmt, views, saves, days=3, handle='a', likes=None, **kw):
    return {'format': fmt, 'views': views, 'saves': saves, 'likes': likes if likes is not None else views // 30,
            'shares': 0, 'created': NOW - days * DAY, 'handle': handle, 'judged': True, **kw}


def history_of(*videos):
    return {str(i): v for i, v in enumerate(videos, 1)}


def background(n=20, rate=0.005):
    """Typical videos without a format: they set the network's typical save rate."""
    return [vid(None, 50_000, int(50_000 * rate), days=5 + i % 20) for i in range(n)]


class StateDir(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = mock.patch.object(state, 'DIR', tmp.name)
        p.start()
        self.addCleanup(p.stop)
        t = mock.patch.object(time, 'time', return_value=NOW)
        t.start()
        self.addCleanup(t.stop)


class VideoRates(unittest.TestCase):
    def test_save_rate_needs_a_real_save_count(self):
        self.assertAlmostEqual(conversion.save_rate({'views': 1000, 'saves': 40}), 0.04)
        self.assertIsNone(conversion.save_rate({'views': 1000}))                       # never read
        self.assertIsNone(conversion.save_rate({'views': 0, 'saves': 0}))              # no views
        self.assertIsNone(conversion.save_rate({'views': 1000, 'saves': 5, 'saves_unknown': True}))
        # a new watchlist video starts with saves 0; a views-only check must not read as "nobody saves it"
        self.assertIsNone(conversion.save_rate({'views': 300_000, 'saves': 0, 'detail_missing': True}))
        self.assertFalse(conversion.too_few_saves({'views': 300_000, 'saves': 0, 'detail_missing': True}, CFG))

    def test_small_videos_and_odd_outliers_are_capped_or_ignored(self):
        c = conversion.conf(CFG)
        self.assertIsNone(conversion.measured_rate({'views': 9_999, 'saves': 900}, c))
        self.assertEqual(conversion.measured_rate({'views': 20_000, 'saves': 10_000}, c), c['rate_cap'])

    def test_record_keeps_the_last_real_numbers_on_a_views_only_check(self):
        e = conversion.record({}, {'saves': 50, 'likes': 900, 'shares': 3})
        self.assertEqual((e['saves'], e['likes']), (50, 900))
        again = conversion.record({}, {'saves': 0, 'likes': 0, 'detail_missing': True}, old=e)
        self.assertEqual(again['saves'], 50)
        self.assertNotIn('saves', conversion.record({}, {'views': 5, 'detail_missing': True}))

    def test_history_keeps_saves_and_older_keys(self):
        h = {'9': {'handle': 'a', 'created': NOW, 'views': 1, 'sorted': True, 'bootstrap_tries': 1, 'saves': 7}}
        main.to_history(h, {'id': '9', 'handle': 'a', 'created': NOW, 'views': 50_000, 'saves': 1500, 'likes': 2000,
                            'shares': 20}, set(), NOW)
        self.assertEqual((h['9']['saves'], h['9']['likes'], h['9']['views']), (1500, 2000, 50_000))
        self.assertTrue(h['9']['sorted'] and h['9']['bootstrap_tries'] == 1)
        main.to_history(h, {'id': '9', 'handle': 'a', 'created': NOW, 'views': 60_000, 'saves': 0, 'likes': 0,
                            'detail_missing': True}, set(), NOW)
        self.assertEqual(h['9']['saves'], 1500)  # views-only check: saves stay
        h['9']['saves_unknown'] = True               # an older failed read ...
        main.to_history(h, {'id': '9', 'handle': 'a', 'created': NOW, 'views': 70_000, 'saves': 2000, 'likes': 1,
                            'shares': 0}, set(), NOW)
        self.assertAlmostEqual(conversion.save_rate(h['9']), 2000 / 70_000)  # ... does not stick


class Triggers(unittest.TestCase):
    def test_the_users_example_is_converting_below_the_viral_bar(self):
        example = {'views': 46_000, 'saves': 1963, 'likes': 1811}
        self.assertTrue(conversion.converting(example, CFG))
        self.assertTrue(conversion.worth_building(example, CFG))

    def test_converting_edges(self):
        c = conversion.conf(CFG)
        at = {'views': c['convert_views'], 'saves': max(c['convert_min_saves'], int(c['convert_views'] * c['convert_save_rate']))}
        self.assertTrue(conversion.converting(at, CFG))
        self.assertFalse(conversion.converting({**at, 'views': c['convert_views'] - 1}, CFG))
        self.assertFalse(conversion.converting({'views': 40_000, 'saves': 299}, CFG))        # too few saves in total
        self.assertFalse(conversion.converting({'views': 40_000, 'saves': 790}, CFG))        # 1.98%: below the rate
        self.assertFalse(conversion.converting({'views': 40_000}, CFG))                      # unknown

    def test_viral_without_saves_never_builds_but_unknown_is_not_blocked(self):
        self.assertFalse(conversion.worth_building({'views': 1_200_000, 'saves': 2000}, CFG))  # 0.17%
        self.assertTrue(conversion.worth_building({'views': 150_000, 'saves': 900}, CFG))      # 0.6%
        self.assertTrue(conversion.worth_building({'views': 150_000}, CFG))                    # unknown
        self.assertFalse(conversion.too_few_saves({'views': 150_000}, CFG))

    def test_level_order(self):
        th = CFG['thresholds']
        young = NOW - 3600
        self.assertEqual(detect.level({'created': young, 'views': 150_000, 'saves': 10}, NOW, None, th, CFG), 'viral')
        self.assertEqual(detect.level({'created': NOW - 3 * DAY, 'views': 46_000, 'saves': 1963}, NOW, None, th, CFG),
                         'converting')
        self.assertEqual(detect.level({'created': young, 'views': 46_000, 'saves': 10}, NOW, None, th, CFG), 'taking_off')
        self.assertIsNone(detect.level({'created': NOW - 3 * DAY, 'views': 46_000, 'saves': 1963}, NOW, None, th))


class Board(unittest.TestCase):
    def test_typical_rate_falls_back_with_few_videos(self):
        c = conversion.conf(CFG)
        self.assertEqual(conversion.baseline(history_of(vid('A', 50_000, 2000)), c, NOW), c['prior_rate'])
        self.assertAlmostEqual(conversion.baseline(history_of(*background()), c, NOW), 0.005)

    def test_format_without_measured_videos_is_average(self):
        b, _ = conversion.board(history_of(*background()), [{'id': 'X'}], CFG, NOW)
        self.assertAlmostEqual(b['X']['conv'], 1.0)
        self.assertIsNone(b['X']['raw_rate'])

    def test_one_great_video_is_pulled_towards_average_but_still_ranks_high(self):
        h = history_of(*background(), vid('ONE', 46_000, 1963), *[vid('MANY', 50_000, 1000) for _ in range(8)])
        b, p0 = conversion.board(h, [{'id': 'ONE'}, {'id': 'MANY'}], CFG, NOW)
        self.assertTrue(1.0 < b['ONE']['conv'] < 0.0427 / p0)
        self.assertGreater(b['MANY']['conv'], 3)  # 2% on 8 videos: proven

    def test_old_and_small_videos_do_not_count(self):
        h = history_of(*background(), vid('F', 50_000, 3000, days=400), vid('F', 5_000, 900))
        b, _ = conversion.board(h, [{'id': 'F'}], CFG, NOW)
        self.assertEqual(b['F']['videos'], 0)


class Ranking(StateDir):
    def test_converting_format_beats_a_viral_only_format(self):
        fmts = [{'id': 'GAME', 'status': 'active'}, {'id': 'LIST', 'status': 'active'}]
        h = history_of(*background(),
                       *[vid('GAME', 300_000, 600) for _ in range(6)],   # viral, 0.2% saved
                       *[vid('LIST', 60_000, 1800) for _ in range(3)])   # not viral, 3% saved
        ids, s = rank.order(h, fmts, CFG)
        self.assertEqual(ids, ['LIST', 'GAME'])
        self.assertFalse(s['GAME']['hot'])  # 6 viral in 7 days, but nobody saves it: not hot

    def test_hot_needs_saves_too(self):
        fmts = [{'id': 'HOT', 'status': 'active'}, {'id': 'LIST', 'status': 'active'}]
        h = history_of(*background(), *[vid('HOT', 300_000, 3000) for _ in range(5)],
                       *[vid('LIST', 60_000, 3000) for _ in range(5)])
        ids, s = rank.order(h, fmts, CFG)
        self.assertTrue(s['HOT']['hot'])
        self.assertEqual(ids[0], 'HOT')  # hot and saved like an average format: first

    def test_reach_still_counts_between_equal_savers(self):
        fmts = [{'id': 'BIG', 'status': 'active'}, {'id': 'SMALL', 'status': 'active'}]
        h = history_of(*background(), *[vid('BIG', 200_000, 3000, days=20) for _ in range(4)],
                       *[vid('SMALL', 12_000, 180, days=20) for _ in range(4)])
        ids, _ = rank.order(h, fmts, CFG)
        self.assertEqual(ids, ['BIG', 'SMALL'])

    def test_hot_update_skips_formats_nobody_saves(self):
        fmts = [{'id': 'GAME', 'status': 'active', 'title': 'g'}]
        h = history_of(*background(), *[vid('GAME', 300_000, 300, days=1) for _ in range(6)])
        meta = {}
        hot.update(h, {}, fmts, CFG, meta, [], dry_run=True)
        self.assertEqual(meta, {})  # dry run: nothing stored ...
        with mock.patch.object(hot.notify, 'push') as push:
            hot.update(h, {}, fmts, CFG, meta, [])
        self.assertEqual(meta['hot'], {})  # ... and not hot
        push.assert_not_called()


class CleanUp(StateDir):
    def plan(self, h, fmts, **cfg):
        c = {**CFG, 'lineup': {**CFG['lineup'], **cfg}}
        return lineup.plan(h, fmts, c, {}, NOW)

    def test_viral_but_not_saved_leaves_even_when_new(self):
        fmts = [{'id': 'GAME', 'status': 'active', 'listed_at': NOW - 2 * DAY},
                *[{'id': f'K{i}', 'status': 'active', 'listed_at': NOW - 60 * DAY} for i in range(3)]]
        h = history_of(*background(), *[vid('GAME', 300_000, 300, days=10) for _ in range(4)])
        p = self.plan(h, fmts, min_formats=1)
        self.assertEqual([f['id'] for f, _, _ in p['out']], ['GAME'])
        self.assertIn('saved by 0.1%', p['out'][0][2])

    def test_new_formats_without_save_data_are_protected(self):
        fmts = [{'id': 'NEW', 'status': 'active', 'listed_at': NOW - 2 * DAY}]
        p = self.plan(history_of(*background()), fmts, min_formats=0)
        self.assertEqual(p['out'], [])
        self.assertIn('less than', p['protected']['NEW'])

    def test_converting_formats_stay_and_viral_protects_only_savers(self):
        fmts = [{'id': 'GOOD', 'status': 'active', 'listed_at': 1},
                {'id': 'VIRALSAVED', 'status': 'active', 'listed_at': 1},
                {'id': 'LOW', 'status': 'active', 'listed_at': 1}]
        h = history_of(*background(),
                       *[vid('GOOD', 40_000, 1200, days=30) for _ in range(3)],
                       vid('VIRALSAVED', 150_000, 900, days=5), vid('VIRALSAVED', 20_000, 120, days=40),
                       vid('LOW', 150_000, 150, days=5), vid('LOW', 50_000, 50, days=40))
        p = self.plan(h, fmts, min_formats=0)
        self.assertEqual([f['id'] for f, _, _ in p['out']], ['LOW'])
        self.assertTrue(p['protected']['VIRALSAVED'])

    def test_list_never_shrinks_below_min_formats_weakest_leave_first(self):
        fmts = [{'id': f'F{i}', 'status': 'active', 'listed_at': 1} for i in range(4)]
        h = history_of(*background(), *[vid(f'F{i}', 50_000, 25 + 10 * i, days=30) for i in range(4) for _ in range(3)])
        p = self.plan(h, fmts, min_formats=2)
        self.assertEqual([f['id'] for f, _, _ in p['out']], ['F0', 'F1'])

    def test_removed_formats_leave_only_the_cleaned_market(self):
        # Balkan ("cleanup": true) loses the format, Slovenia ("cleanup": false) keeps it (user's rule, 16 Oct 2026)
        fmts = [{'id': 'GAME', 'status': 'active', 'title': 'Igra', 'page_id': 'p1', 'pages': {'sl': 'p2'}, 'listed_at': 1},
                {'id': 'K', 'status': 'active', 'title': 'k', 'listed_at': 1}]
        h = history_of(*background(), *[vid('GAME', 300_000, 300, days=10) for _ in range(4)])
        mkts = [{'key': 'sh', 'archive_page': 'arch-sh', 'holder_page': 'list-sh', 'T': {'flag': 'BA'}},
                {'key': 'sl', 'archive_page': 'arch-sl', 'holder_page': 'list-sl', 'T': {'flag': 'SI'}}]
        cfg = {**CFG, 'lineup': {**CFG['lineup'], 'min_formats': 1}}
        with mock.patch.object(lineup.notion, 'move_page') as move, mock.patch.object(lineup.notify, 'push') as push, \
                mock.patch.object(main, 'load_config', return_value=cfg):
            lineup.apply(h, fmts, cfg, {}, mkts, NOW)
        move.assert_called_once_with('p1', 'arch-sh')
        g = fmts[0]
        self.assertEqual((g['status'], g['only_markets'], g['cleaned_from'], g['dropped_pages']),
                         ('active', ['sl'], ['sh'], {'sh': 'p1'}))
        self.assertIsNone(main.page_of(g, 'sh'))
        self.assertEqual(main.page_of(g, 'sl'), 'p2')
        self.assertIn('stays in SI', push.call_args[0][1])
        # the next clean-up does not judge it again (no cleaned market left), Slovenia keeps it
        self.assertEqual(lineup.plan(h, fmts, cfg, {}, NOW)['out'], [])
        # a viral + saved video brings it back into the Balkan list
        with mock.patch.object(main.notion, 'move_page') as move, mock.patch.object(main, 'load_config', return_value=cfg):
            self.assertEqual(main.restore_market_page(g, mkts[0]), 'p1')
        move.assert_called_once_with('p1', 'list-sh')
        self.assertEqual((main.page_of(g, 'sh'), g.get('only_markets'), g['cleaned_from']), ('p1', None, []))

    def test_slovenian_only_formats_are_never_cleaned(self):
        fmts = [{'id': 'SLO', 'status': 'active', 'only_markets': ['sl'], 'listed_at': 1}]
        h = history_of(*background(), *[vid('SLO', 50_000, 20, days=10) for _ in range(4)])
        self.assertEqual(self.plan(h, fmts, min_formats=0)['out'], [])

    def test_a_format_only_in_the_cleaned_market_is_archived(self):
        fmts = [{'id': 'BA', 'status': 'active', 'only_markets': ['sh'], 'page_id': 'p1', 'title': 'b', 'listed_at': 1}]
        h = history_of(*background(), *[vid('BA', 300_000, 300, days=10) for _ in range(4)])
        cfg = {**CFG, 'lineup': {**CFG['lineup'], 'min_formats': 0}}
        mkts = [{'key': 'sh', 'archive_page': 'arch-sh', 'T': {'flag': 'BA'}}]
        with mock.patch.object(lineup.notion, 'move_page'), mock.patch.object(lineup.notify, 'push'), \
                mock.patch.object(main, 'load_config', return_value=cfg):
            lineup.apply(h, fmts, cfg, {}, mkts, NOW)
        self.assertEqual(fmts[0]['status'], 'archived')
        self.assertIn('saved by', fmts[0]['archived_reason'])


class Alerts(StateDir):
    def test_viral_with_unknown_saves_waits_for_a_full_check(self):
        v = {'id': '1', 'handle': 'a', 'created': NOW - DAY, 'views': 300_000, 'url': 'u', 'notified': []}
        with mock.patch.object(main, 'handle_viral') as hv:
            r = main.handle_alert(v, 'viral', [], [], {}, CFG, NOW, False, False)
        hv.assert_not_called()
        self.assertEqual(r['deferred'], 'saves unknown')
        with mock.patch.object(main, 'handle_viral', return_value={'ok': 1}) as hv:  # 6+ days: goes ahead
            main.handle_alert({**v, 'created': NOW - 6 * DAY - 1}, 'viral', [], [], {}, CFG, NOW, False, False)
        hv.assert_called_once()

    def test_converting_video_is_judged_like_a_viral_one(self):
        v = {'id': '1', 'handle': 'a', 'created': NOW - DAY, 'views': 46_000, 'saves': 1963, 'url': 'u', 'notified': []}
        with mock.patch.object(main, 'handle_viral', return_value={'ok': 1}) as hv:
            main.handle_alert(v, 'converting', [], [], {}, CFG, NOW, False, False)
        self.assertIn('4.3%', hv.call_args.kwargs['label'])

    def run_viral(self, v, fmts, verdict, history=None):
        with mock.patch.object(main.media, 'download', return_value='f.mp4'), \
                mock.patch.object(main.media, 'audio', return_value='a.mp3'), \
                mock.patch.object(main.soniox, 'transcribe', return_value={'text': 'x'}), \
                mock.patch.object(main.classify, 'judge', return_value=verdict), \
                mock.patch.object(main, 'build_format') as build, mock.patch.object(main, 'revive_format', return_value=(True, 1, [])) as revive, \
                mock.patch.object(main.notify, 'push') as push, mock.patch.object(main.notify, 'radar'):
            r = main.handle_viral(v, [], fmts, history or {}, CFG, NOW, False)
        return r, build, revive, push

    def test_viral_video_nobody_saves_does_not_build_a_format(self):
        v = {'id': '1', 'handle': 'a', 'created': NOW - DAY, 'views': 1_000_000, 'saves': 1000, 'likes': 90_000,
             'url': 'u', 'notified': []}
        r, build, _, push = self.run_viral(v, [], {'duplicate_of': None, 'english_script': 's'})
        build.assert_not_called()
        self.assertIn('too few saves', push.call_args[0][1])
        self.assertIn('viral', v['notified'])

    def test_archived_format_comes_back_only_when_the_video_is_saved(self):
        arch = {'id': 'A', 'status': 'archived', 'title': 't'}
        h = history_of(*background())
        low = {'id': '1', 'handle': 'a', 'created': NOW - DAY, 'views': 200_000, 'saves': 1100, 'likes': 1, 'url': 'u',
               'notified': []}                                   # saved by 0.55%
        _, _, revive, _ = self.run_viral(dict(low), [arch], {'duplicate_of': 'A'}, h)
        revive.assert_called_once()                              # 0.55% >= typical 0.5%: comes back
        _, _, revive, push = self.run_viral({**low, 'saves': 600}, [arch], {'duplicate_of': 'A'}, h)
        revive.assert_not_called()                               # 0.3%: blocked (too few saves)
        self.assertIn('too few saves', push.call_args[0][1])
        h2 = history_of(*background(rate=0.01))                 # typical video 1%
        _, _, revive, push = self.run_viral(dict(low), [arch], {'duplicate_of': 'A'}, h2)
        revive.assert_not_called()                               # 0.55% < typical 1%
        self.assertIn('less than a typical video', push.call_args[0][1])


class ComesBack(StateDir):
    def test_a_format_cleaned_out_of_the_balkans_comes_back_with_a_saved_viral_video(self):
        f = {'id': 'G', 'status': 'active', 'title': 'g', 'only_markets': ['sl'], 'cleaned_from': ['sh'],
             'dropped_pages': {'sh': 'p1'}, 'pages': {'sl': 'p2'}}
        h = history_of(*background())
        v = {'id': '1', 'handle': 'a', 'created': NOW - DAY, 'views': 200_000, 'saves': 2000, 'likes': 1, 'url': 'u',
             'notified': []}
        mkts = [{'key': 'sh', 'holder_page': 'list-sh', 'T': {'flag': 'BA'}}, {'key': 'sl', 'T': {'flag': 'SI'}}]
        with mock.patch.object(main.media, 'download', return_value='f'), mock.patch.object(main.media, 'audio'), \
                mock.patch.object(main.soniox, 'transcribe', return_value={'text': 'x'}), \
                mock.patch.object(main.classify, 'judge', return_value={'duplicate_of': 'G'}), \
                mock.patch.object(main.notion, 'move_page') as move, mock.patch.object(main, 'rerank'), \
                mock.patch.object(main, 'ensure_market_pages', return_value=[]), \
                mock.patch.object(main, 'list_position', return_value=3), mock.patch.object(main, 'load_config', return_value=CFG), \
                mock.patch.object(main.notify, 'push') as push, mock.patch.object(main.notify, 'radar'):
            main.handle_viral(v, mkts, [f], h, CFG, NOW, False)
        move.assert_called_once_with('p1', 'list-sh')
        self.assertEqual((main.page_of(f, 'sh'), f.get('only_markets')), ('p1', None))
        self.assertIn('BA', push.call_args[0][1])

    def test_a_viral_video_nobody_saves_does_not_bring_it_back(self):
        f = {'id': 'G', 'status': 'active', 'title': 'g', 'only_markets': ['sl'], 'cleaned_from': ['sh'],
             'dropped_pages': {'sh': 'p1'}, 'pages': {'sl': 'p2'}}
        v = {'id': '1', 'handle': 'a', 'created': NOW - DAY, 'views': 900_000, 'saves': 300, 'likes': 1, 'url': 'u',
             'notified': []}
        with mock.patch.object(main.media, 'download', return_value='f'), mock.patch.object(main.media, 'audio'), \
                mock.patch.object(main.soniox, 'transcribe', return_value={'text': 'x'}), \
                mock.patch.object(main.classify, 'judge', return_value={'duplicate_of': 'G'}), \
                mock.patch.object(main.notion, 'move_page') as move, mock.patch.object(main, 'list_position', return_value=None), \
                mock.patch.object(main.notify, 'push'), mock.patch.object(main.notify, 'radar'):
            main.handle_viral(v, [{'key': 'sh', 'T': {'flag': 'BA'}}], [f], history_of(*background()), CFG, NOW, False)
        move.assert_not_called()
        self.assertEqual(f['cleaned_from'], ['sh'])


class Backfill(unittest.TestCase):
    def test_reads_newest_first_and_gives_up_after_three_failures(self):
        h = {'1': {'handle': 'a', 'created': NOW - 5 * DAY, 'views': 50_000},
             '2': {'handle': 'a', 'created': NOW - 2 * DAY, 'views': 50_000},
             '3': {'handle': 'a', 'created': NOW - 2 * DAY, 'views': 5_000},             # too small
             '4': {'handle': 'a', 'created': NOW - 300 * DAY, 'views': 900_000},         # too old
             '5': {'handle': 'a', 'created': NOW - DAY, 'views': 50_000, 'saves': 10}}   # already known
        calls = []

        def detail(handle, i):
            calls.append(i)
            return {'views': 60_000, 'saves': 1200, 'likes': 3000, 'shares': 1, 'desc': 'd'} if i == '2' else None

        out = conversion.backfill(h, 5, NOW, detail)
        self.assertEqual(calls, ['2', '1'])
        self.assertEqual(([d['id'] for d in out], h['2']['saves'], h['2']['views']), (['2'], 1200, 60_000))
        conversion.backfill(h, 5, NOW, detail)
        conversion.backfill(h, 5, NOW, detail)
        self.assertTrue(h['1']['saves_unknown'])
        calls.clear()
        conversion.backfill(h, 5, NOW, detail)
        self.assertEqual(calls, [])

    def test_only_unsorted_videos_are_sorted(self):
        h = {'1': {'format': 'X'}, '2': {'judged': True}, '3': {}, '4': {'sorted': True}}
        self.assertEqual([d['id'] for d in conversion.to_sort(h, [{'id': k} for k in h])], ['3'])

    def test_read_saves_sorts_backfilled_videos_into_formats(self):
        h = {'1': {'handle': 'a', 'created': NOW - DAY, 'views': 50_000}}
        with mock.patch.object(main.tiktok, 'video_detail', return_value={'views': 50_000, 'saves': 900, 'likes': 1,
                                                                          'shares': 0, 'desc': 'd'}), \
                mock.patch.object(main.classify, 'classify_many', return_value={'1': {'match': 'F', 'hook_en': 'h'}}):
            main.read_saves(h, [], CFG, NOW)
        self.assertEqual((h['1']['format'], h['1']['saves'], h['1']['sorted']), ('F', 900, True))


if __name__ == '__main__':
    unittest.main()


class ListText(StateDir):
    def test_list_instructions_are_written_into_the_fire_box_only(self):
        from watcher import markets, setup
        state.save('notion.json', {'markets': {'sh': {'list_page': 'L1'}, 'sl': {'list_page': 'L2'}}})
        blocks = [{'id': 'h', 'type': 'heading_1'}, {'id': 'pg', 'type': 'child_page'},
                  {'id': 'rule', 'type': 'callout', 'callout': {'icon': {'emoji': '🚨'}}},
                  {'id': 'fire', 'type': 'callout', 'callout': {'icon': {'emoji': '🔥'}}}]
        with mock.patch.object(setup.notion, 'children', return_value=blocks), \
                mock.patch.object(setup.notion, 'api') as api:
            self.assertEqual(setup.list_text(CFG), ['sh', 'sl'])
        self.assertEqual([c.args[1] for c in api.call_args_list], ['/blocks/fire', '/blocks/fire'])
        sent = ''.join(x['text']['content'] for x in api.call_args_list[0].args[2]['callout']['rich_text'])
        self.assertIn('spremaju', sent)
        self.assertIn('100.000', sent)
        self.assertEqual(markets.avoid_found('sh', ' '.join(markets.TEXT['sh']['list_fire'])), [])  # ijekavian
        self.assertIn('shrani', ' '.join(markets.TEXT['sl']['list_fire']))

    def test_missing_fire_box_stops(self):
        from watcher import setup
        state.save('notion.json', {'markets': {'sh': {'list_page': 'L1'}}})
        with mock.patch.object(setup.notion, 'children', return_value=[]), mock.patch.object(setup.notion, 'api'):
            with self.assertRaises(SystemExit):
                setup.list_text({**CFG, 'markets': {'sh': CFG['markets']['sh']}})


class AgeBoxes(StateDir):
    LINES = ['Besedilo na zaslonu: Izpitna vprašanja vnaprej? 😳',
             'Torej, prišla sem do četrtega letnika faksa, da sem šele zdaj izvedela, da bi lahko vnaprej poznala izpitna vprašanja.',
             'Najboljše pa je, da ji je med učenjem celo zanimivo.',
             'Komentiraj »VPRAŠANJA« in pošljem ti link do aplikacije.']

    def blocks(self):
        return [{'id': f'b{i}', 'type': 'paragraph', 'text': t} for i, t in enumerate(self.LINES)]

    def test_age_box_is_one_short_tip(self):
        from watcher import ages
        with mock.patch.object(ages.llm, 'chat_json', return_value={'tip': 'Če ne hodiš na faks, namesto »četrtega letnika faksa« povej svoj razred.'}):
            found = ages.variants(self.LINES, 'sl')
        text = ''.join(x['text']['content'] for x in ages.box(found, 'sl')['callout']['rich_text'])
        self.assertEqual(text, 'Nasvet za tvojo starost: Če ne hodiš na faks, namesto »četrtega letnika faksa« povej svoj razred.')
        for empty in ({'tip': ''}, {'tip': 'x' * 300}, {'tip': 'Komentiraj »X« in pošljem ti link do aplikacije.'}):
            with mock.patch.object(ages.llm, 'chat_json', return_value=empty):
                self.assertEqual(ages.variants(self.LINES, 'sl'), [])

    def test_box_goes_after_the_cta_and_only_once(self):
        from watcher import ages
        found = [{'tip': 'Če hodiš v srednjo, namesto »četrtega letnika faksa« povej »četrtega letnika srednje«.'}]
        with mock.patch.object(ages.notion, 'children', return_value=self.blocks()), \
                mock.patch.object(ages, 'variants', return_value=found), mock.patch.object(ages.notion, 'api') as api:
            r = ages.add_to_page('P', 'sl', script_blocks=lambda pid: self.blocks(), plain=lambda b: b['text'])
        self.assertEqual(r, 'added')
        body = api.call_args.args[2]
        self.assertEqual(body['after'], 'b3')  # after the CTA line
        text = ''.join(x['text']['content'] for x in body['children'][0]['callout']['rich_text'])
        self.assertIn('Nasvet za tvojo starost: Če hodiš v srednjo', text)
        self.assertNotIn('🎥', text)
        with_box = self.blocks() + [{'type': 'callout', 'callout': {'icon': {'emoji': '🎓'}}}]
        with mock.patch.object(ages.notion, 'children', return_value=with_box), mock.patch.object(ages, 'variants') as v:
            self.assertEqual(ages.add_to_page('P', 'sl'), 'had')
        v.assert_not_called()

    def test_redo_replaces_the_old_box_after_the_new_one_is_in(self):
        from watcher import ages
        old = {'id': 'old', 'type': 'callout', 'callout': {'icon': {'emoji': '🎓'}}}
        found = [{'tip': 'Če hodiš v srednjo, namesto »četrtega letnika faksa« povej »četrtega letnika srednje«.'}]
        with mock.patch.object(ages.notion, 'children', return_value=self.blocks() + [old]), \
                mock.patch.object(ages, 'variants', return_value=found) as v, mock.patch.object(ages.notion, 'api') as api:
            r = ages.add_to_page('P', 'sl', script_blocks=lambda pid: self.blocks(), plain=lambda b: b['text'], redo=True)
        self.assertEqual(r, 'added')
        self.assertEqual([c.args[0] for c in api.call_args_list], ['PATCH', 'DELETE'])
        self.assertTrue(all('🎥' not in line for line in v.call_args.args[0]))

    def test_redo_without_a_tip_removes_the_old_box(self):
        from watcher import ages
        old = {'id': 'old', 'type': 'callout', 'callout': {'icon': {'emoji': '🎓'}}}
        with mock.patch.object(ages.notion, 'children', return_value=self.blocks() + [old]), \
                mock.patch.object(ages, 'variants', return_value=[]), mock.patch.object(ages.notion, 'api') as api:
            r = ages.add_to_page('P', 'sl', redo=True, script_blocks=lambda pid: self.blocks(), plain=lambda b: b['text'])
        self.assertEqual(r, 'none')
        api.assert_called_once_with('DELETE', '/blocks/old')

    def test_scripts_that_fit_every_age_get_no_box_and_bad_text_is_held(self):
        from watcher import ages
        kw = dict(script_blocks=lambda pid: self.blocks(), plain=lambda b: b['text'])
        with mock.patch.object(ages.notion, 'children', return_value=self.blocks()), \
                mock.patch.object(ages, 'variants', return_value=[]), mock.patch.object(ages.notion, 'api') as api:
            self.assertEqual(ages.add_to_page('P', 'sl', **kw), 'none')
        api.assert_not_called()
        bad = [{'tip': 'Uvek imam vreme sa Astra AI'}]
        with mock.patch.object(ages.notion, 'children', return_value=self.blocks()), \
                mock.patch.object(ages, 'variants', return_value=bad), mock.patch.object(ages.notion, 'api') as api:
            r = ages.add_to_page('P', 'sh', **kw)
        self.assertTrue(r.startswith('held') and 'other app' in r and 'ekavian' in r)
        api.assert_not_called()

    def test_each_page_is_checked_once_and_again_after_a_rebuild(self):
        fmts = [{'id': 'F', 'status': 'active', 'title': 't', 'page_id': 'p1', 'pages': {'sl': 'p2'}}]
        mkts = [{'key': 'sh', 'lang': 'sh'}, {'key': 'sl', 'lang': 'sl'}]
        with mock.patch.object(main.ages, 'add_to_page', return_value='none') as add:
            main.age_boxes(fmts, mkts, CFG)
            main.age_boxes(fmts, mkts, CFG)
            self.assertEqual(add.call_count, 2)
            fmts[0]['pages']['sl'] = 'p3'                      # rebuilt page
            main.age_boxes(fmts, mkts, CFG)
            self.assertEqual(add.call_count, 3)
        with mock.patch.object(main.ages, 'add_to_page', return_value='held: x') as add:
            fmts[0]['page_id'] = 'p9'
            for _ in range(5):
                main.age_boxes(fmts, mkts, CFG)
            self.assertEqual(add.call_count, 3)                # held pages: 3 tries, then left alone
        with mock.patch.object(main.ages, 'add_to_page', return_value='none') as add:
            fmts.append({'id': 'G', 'status': 'active', 'title': 'g', 'page_id': 'q1', 'pages': {'sl': 'q2'}})
            main.age_boxes(fmts, mkts, CFG, limit=1)
            self.assertEqual(add.call_count, 1)                # a few pages per run


class PageUpkeep(StateDir):
    def test_a_rewritten_page_gets_its_age_box_back(self):
        fmts = [{'id': 'F', 'status': 'active', 'title': 't', 'page_id': 'p1', 'only_markets': ['sh'],
                 'age': {'sh': {'page': 'p1', 'status': 'added', 'tries': 1}}}]
        mkts = [{'key': 'sh', 'lang': 'sh'}]
        box = [{'type': 'callout', 'callout': {'icon': {'emoji': '🎓'}}}]
        with mock.patch.object(main.notion, 'children', return_value=box), \
                mock.patch.object(main.ages, 'add_to_page') as add:
            main.age_boxes(fmts, mkts, CFG)
        add.assert_not_called()                                 # box still there: nothing to do
        with mock.patch.object(main.notion, 'children', return_value=[]), \
                mock.patch.object(main.ages, 'add_to_page', return_value='added') as add:
            main.age_boxes(fmts, mkts, CFG)
        add.assert_called_once()                                # box gone after a rebuild: written again

    def test_cta_is_added_once_and_pages_without_a_word_are_reported(self):
        fmts = [{'id': 'A20261008204718', 'status': 'active', 'title': 'Popusti', 'page_id': 'p1', 'only_markets': ['sh']},
                {'id': 'NOWORD', 'status': 'active', 'title': 'new', 'page_id': 'p2', 'only_markets': ['sh']}]
        mkts = [{'key': 'sh', 'lang': 'sh', 'T': {'silent_label': 'Tekst na ekranu – ne izgovaraj:'}}]
        script = [{'id': 'b1', 'type': 'paragraph', 'paragraph': {'rich_text': [{'plain_text': 'Popusti za studente.'}]}}]
        with mock.patch.object(main.reword, 'script_blocks', return_value=script), \
                mock.patch.object(main.notion, 'api') as api:
            r = main.add_cta(fmts, mkts)
        self.assertEqual(len(r['added']), 1)
        self.assertIn('»POPUST«', r['added'][0])
        self.assertEqual(api.call_args.args[2]['after'], 'b1')
        self.assertEqual(r['missing_word'], ['sh new (no word)'])
        done = script + [{'id': 'b2', 'type': 'paragraph', 'paragraph': {'rich_text': [
            {'plain_text': 'Komentariši »POPUST« i poslaću ti link do aplikacije.'}]}}]
        with mock.patch.object(main.reword, 'script_blocks', return_value=done), mock.patch.object(main.notion, 'api') as api:
            r = main.add_cta(fmts, mkts)
        self.assertEqual(len(r['had']), 2)
        api.assert_not_called()


class CtaLength(unittest.TestCase):
    def test_the_cta_never_counts_against_the_originals_length(self):
        from watcher import align, markets
        line = 'Komentiraj »POPUST« in pošljem ti link do aplikacije.'
        self.assertEqual(align._words(markets.strip_cta('Prvi stavek. ' + line)), 2)
        self.assertEqual(markets.strip_cta('Brez CTA.').strip(), 'Brez CTA.')
        body = 'beseda ' * 90
        spec = {'script': [{'cue': 'memo', 'text': 'Memo AI ' + body}, {'cue': None, 'text': line}]}
        why = align._validate(spec, 90, source='', lang='sl', own_ex=False)
        self.assertNotIn('words', why or '')                  # 92 + 8 CTA words: still within 110% of 90
        spec['script'][0]['text'] = 'Memo AI ' + 'beseda ' * 99
        self.assertIn('words', align._validate(spec, 90, source='', lang='sl', own_ex=False))


class AppLink(unittest.TestCase):
    def test_missing_app_link_goes_to_the_memo_line_and_the_materials_box(self):
        from watcher import reword
        para = lambda i, t, link=None: {'id': i, 'type': 'paragraph', 'paragraph': {'rich_text': [
            {'type': 'text', 'plain_text': t, 'text': {'content': t, **({'link': {'url': link}} if link else {})}}]}}
        script = [para('s1', 'Diva, vidim same petke.'), para('s2', 'Memo AI ti sam dela zapiske.')]
        box = {'id': 'm', 'type': 'callout', 'callout': {'icon': {'emoji': '💡'}, 'rich_text': [
            {'type': 'text', 'plain_text': '📎 Logotip', 'text': {'content': '📎 Logotip'}}]}}
        link = 'https://memoai.eu/creator'
        with mock.patch.object(reword, 'script_blocks', return_value=script), \
                mock.patch.object(reword.notion, 'children', return_value=script + [box]), \
                mock.patch.object(reword.notion, 'api') as api:
            self.assertEqual(reword.ensure_app_link('P', link, 'sl'), ['script', 'materials'])
        (_, p1, b1), (_, p2, b2) = [c.args for c in api.call_args_list]
        self.assertEqual(p1, '/blocks/s2')                                   # the line that names Memo AI
        self.assertEqual(b1['paragraph']['rich_text'][1]['text']['link']['url'], link)
        self.assertEqual(b2['callout']['rich_text'][0]['text']['link']['url'], link)
        self.assertEqual(b2['callout']['rich_text'][-1]['text']['content'], '📎 Logotip')
        linked = [script[0], para('s2', '🎥 Posnemi Memo AI', link)]
        box['callout']['rich_text'].append({'type': 'text', 'plain_text': 'x', 'text': {'content': 'x', 'link': {'url': link}}})
        with mock.patch.object(reword, 'script_blocks', return_value=linked), \
                mock.patch.object(reword.notion, 'children', return_value=linked + [box]), \
                mock.patch.object(reword.notion, 'api') as api:
            self.assertEqual(reword.ensure_app_link('P', link, 'sl'), [])     # already there: untouched
        api.assert_not_called()
