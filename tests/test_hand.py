import json
import unittest
from unittest import mock

from watcher import hand

LINKS = {'folder': 'https://drive/folder', 'mac': 'https://drive/mac', 'windows': 'https://drive/win',
         'iphone': 'https://drive/iphone', 'android': 'https://drive/android'}


def text(blocks):
    return json.dumps(blocks, ensure_ascii=False)


class HandScripts(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(hand, 'demo_links', return_value=LINKS)
        p.start()
        self.addCleanup(p.stop)

    def test_every_script_has_both_languages_one_demo_mark_and_a_cta_word(self):
        keys = [f['key'] for f in hand.formats()]
        self.assertEqual(len(keys), len(set(keys)))
        for f in hand.formats():
            for lang in ('sl', 'sh'):
                spec = f[lang]
                self.assertEqual(sum(p.count(hand.DEMO) for p in spec['script']), 1, (f['key'], lang))
                for k in ('title', 'hook', 'cta_word', 'age_tip'):
                    self.assertTrue(spec[k], (f['key'], lang, k))

    def test_page_has_the_demo_cue_where_the_mark_was_and_ends_the_script_with_the_cta(self):
        f = hand.formats()[0]
        blocks = hand.page_blocks(f, 'sl', 'https://lab', 'LOGO')
        t = text(blocks)
        self.assertNotIn(hand.DEMO, t)
        self.assertIn('🎥 Tukaj predvajaj Memo AI demo', t)
        self.assertIn('https://drive/folder', t)
        self.assertIn('https://drive/iphone', t)
        self.assertIn(f"Komentiraj »{f['sl']['cta_word']}« in pošljem ti link do aplikacije.", t)
        self.assertEqual(blocks[-1]['type'], 'image')  # the Memo AI logo closes the materials
        self.assertIn('🎓', t)  # the age tip under the CTA, like the built pages

    def test_balkan_page_uses_the_balkan_texts(self):
        f = hand.formats()[0]
        t = text(hand.page_blocks(f, 'sh', None, None))
        self.assertIn('🎥 Ovdje pusti Memo AI demo', t)
        self.assertIn(f"Komentariši »{f['sh']['cta_word']}« i poslaću ti link do aplikacije.", t)
        self.assertNotIn('Visual Hook Lab', t)

    def test_tail_keeps_registry_order_and_skips_unbuilt(self):
        keys = [f['key'] for f in hand.formats()]
        built = {'sl': {keys[2]: 'p3', keys[0]: 'p1'}}
        with mock.patch.object(hand, 'pages', return_value=built):
            self.assertEqual(hand.tail('sl'), ['p1', 'p3'])
            self.assertEqual(hand.tail('sh'), [])


if __name__ == '__main__':
    unittest.main()
