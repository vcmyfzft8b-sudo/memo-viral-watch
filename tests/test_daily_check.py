"""Once a day the run builds missing pages again and runs verify; problems reach Discord (user's request, 16 Oct 2026)."""
from unittest import mock

from watcher import main, verify

DAY = 86400
NOW = 1792130000


def check(meta, problems, now=NOW, fill=True):
    pushed = []
    with mock.patch.object(verify, 'run', return_value=problems), \
            mock.patch.object(main.state, 'save'), \
            mock.patch.object(main, 'fill_market') as fill_market, \
            mock.patch.object(main, 'load_formats', return_value=[]), \
            mock.patch.object(main.notify, 'push', side_effect=lambda t, m, *a, **k: pushed.append(m)):
        main.daily_check([{'id': 'A1', 'status': 'active', 'title': 'X'}], [{'key': 'sl'}], {}, meta, now, fill=fill)
    return pushed, fill_market


def test_once_a_day_and_new_problems_alert_at_once():
    meta = {}
    with mock.patch.object(main, 'page_of', return_value=None), mock.patch.object(main.M, 'of', return_value=[{'key': 'sl'}]):
        pushed, fill_market = check(meta, ['🇸🇮 X: no page (held: failed: too long)'])
    fill_market.assert_called_once_with('sl')
    assert len(pushed) == 1 and 'New:' in pushed[0] and 'held: failed' in pushed[0]
    pushed, fill_market = check(meta, ['🇸🇮 X: no page'])  # same day: nothing runs again
    assert not pushed and not fill_market.called


def test_open_problem_reminds_every_3_days_only():
    meta = {}
    check(meta, ['🇸🇮 X: no page (held: a)'])
    pushed, _ = check(meta, ['🇸🇮 X: no page (held: b)'], now=NOW + DAY, fill=False)  # same problem, new reason
    assert not pushed
    pushed, _ = check(meta, ['🇸🇮 X: no page (held: c)'], now=NOW + 3 * DAY, fill=False)
    assert len(pushed) == 1 and 'Still open:' in pushed[0]


def test_nothing_wrong_sends_nothing():
    meta = {'open_problems': ['old']}
    pushed, _ = check(meta, [], fill=False)
    assert not pushed and meta['open_problems'] == []
