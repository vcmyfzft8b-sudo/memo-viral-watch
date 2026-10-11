"""Every link creators can click works (part of mode verify, read-only).

Walks the root page, each market's guide, list and Visual Hook Lab, and every live format page, and opens every link:
- websites (memoai.eu, …): must answer without an error (redirects followed);
- TikTok videos: must still be available (a deleted/private example or original is reported);
- Notion links and page mentions: the page must exist and not be in the trash;
- videos/images: must have a file.
Results are cached per URL, so a link used on many pages is opened once.
"""
import re

import requests

from . import notion, tiktok

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'}
NOTION_ID = re.compile(r'([0-9a-f]{32})(?:[?#]|$)')


def links_of(block):
    """(kind, target) of every link in one block: ('url', …), ('page', id), ('media', ok)."""
    t = block['type']
    data = block.get(t) or {}
    out = []
    for x in data.get('rich_text', []) or []:
        url = ((x.get('text') or {}).get('link') or {}).get('url')
        if url:
            out.append(('url', url))
        m = x.get('mention') or {}
        if m.get('type') == 'page':
            out.append(('page', m['page']['id']))
        elif m.get('type') in ('link_preview', 'link_mention'):
            out.append(('url', (m.get(m['type']) or {}).get('url', '')))
    if t in ('bookmark', 'embed', 'link_preview') and data.get('url'):
        out.append(('url', data['url']))
    if t == 'link_to_page':
        out.append(('page', data.get('page_id') or data.get('database_id')))
    if t in ('video', 'image', 'file', 'pdf'):
        kind = data.get('type')
        if kind == 'external':
            out.append(('url', (data.get('external') or {}).get('url', '')))
        else:
            out.append(('media', bool((data.get(kind) or {}).get('url') or kind == 'file_upload')))
    return out


def walk(block_id):
    """All blocks of a page, without going into sub-pages (those are checked on their own)."""
    for b in notion.children(block_id):
        yield b
        if b.get('has_children') and b['type'] not in ('child_page', 'child_database'):
            yield from walk(b['id'])


class Checker:
    def __init__(self):
        self.cache = {}

    def page_ok(self, pid):
        key = 'page:' + pid.replace('-', '')
        if key not in self.cache:
            try:
                p = notion.api('GET', f'/pages/{pid}')
                self.cache[key] = None if not (p.get('archived') or p.get('in_trash')) else 'Notion page is in the trash'
            except Exception as e:
                self.cache[key] = f'Notion page not found ({str(e)[:60]})'
        return self.cache[key]

    def url_ok(self, url):
        if not url:
            return 'empty link'
        if url in self.cache:
            return self.cache[url]
        why = None
        if re.search(r'notion\.(so|site|com)/', url):
            m = NOTION_ID.search(url.split('?')[0].replace('-', '')) or NOTION_ID.search(url.replace('-', ''))
            why = self.page_ok(m.group(1)) if m else None
        elif 'tiktok.com/' in url:
            m = re.search(r'@([^/?]+)/video/(\d+)', url)
            if m:
                try:
                    why = None if tiktok.video_detail(*m.groups()) else 'TikTok video unavailable (deleted or private?)'
                except Exception as e:
                    why = f'TikTok check failed ({str(e)[:60]})'
        else:
            try:
                r = requests.get(url, headers=UA, timeout=30, allow_redirects=True)
                why = None if r.status_code < 400 else f'HTTP {r.status_code}'
            except requests.RequestException as e:
                why = f'not reachable ({str(e)[:60]})'
        self.cache[url] = why
        return why

    def page(self, pid, name):
        """Problems of one page's links."""
        out = []
        for b in walk(pid):
            for kind, target in links_of(b):
                why = (self.url_ok(target) if kind == 'url' else self.page_ok(target) if kind == 'page'
                       else None if target else 'video/image without a file')
                if why:
                    out.append(f'{name}: broken link {str(target)[:90]} – {why}')
        return out


def run(cfg, fmts, page_of, pages):
    """Returns (problems, number of links opened)."""
    from .markets import TEXT
    c, problems = Checker(), []
    if pages.get('root'):
        problems += c.page(pages['root'], 'root page')
    for key, m in cfg['markets'].items():
        flag, mp = TEXT[m['lang']]['flag'], pages['markets'][key]
        for part in ('guide', 'list_page', 'visual_hook_lab'):
            pid = mp.get(part) or ''
            pid = pid.rstrip('/').split('/')[-1].split('-')[-1].split('?')[0] if pid.startswith('http') else pid
            if pid:
                problems += c.page(pid, f'{flag} {part}')
        for f in fmts:
            if f.get('status') == 'active' and page_of(f, key):
                problems += c.page(page_of(f, key), f"{flag} {f['title']}")
    return problems, len(c.cache)
