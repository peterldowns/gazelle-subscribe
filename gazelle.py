#!/usr/bin/env python
# coding: utf-8
import requests
import urllib.parse as urlparse
import lxml.html
import re
from datetime import datetime


def to_number(s):
    return int(re.sub(r'[^\d]', '', s))


def parse_collages(tree):
    table = tree.find_class('collage_table')
    table = table and table[0] or None
    if table is None:
        raise Exception('could not find collage table')
    _, *rows = table.iterchildren()
    for row in rows:
        collage = {}
        columns = list(row)
        collage['category'] = columns[0].text_content().strip().lower()
        link = columns[1].find('a')
        collage['name'] = link.text_content().strip()
        url = link.attrib['href']
        collage['url'] = url
        p = urlparse.urlparse(url)
        collage['id'] = urlparse.parse_qs(p.query)['id'][0]
        collage['torrents'] = to_number(columns[2].text_content())
        collage['subscribers'] = to_number(columns[3].text_content())
        update_str = columns[4].find('span').attrib['title']
        # Can be parsed with
        #   datetime.strptime(update_str, '%b %d %Y, %H:%M')
        # but then can't dump to JSON, so leaving as string like this.
        collage['updated'] = update_str.strip().lower()
        yield collage



class Session(requests.Session):
    HEADERS = {
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) '
                      'AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.79 '
                      'Safari/535.11',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9 '
                  ',*/*;q=0.8',
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Accept-Language': 'en-US,en;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'
    }


    def __init__(self, hostname, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        self.headers.update(Session.HEADERS)

        parsed = urlparse.urlparse(hostname)
        host = parsed.netloc
        if not host:
            host, _ = urlparse.splithost(parsed.path)
        self.hostname = 'https://{}'.format(host)

    def url(self, path):
        return urlparse.urljoin(self.hostname, path)

    def login(self, username, password):
        data = {'username': username, 'password': password}
        r = self.post(self.url('login.php'), data=data)
        return r.status_code == 200

    def list_bookmarked_collages(self):
        data = {'type': 'collages', 'page': 1}
        collages = []
        while True:
            r = self.get(self.url('bookmarks.php'), params=data)
            if not r.status_code == 200:
                return
            tree = lxml.html.fromstring(r.content)
            collages.extend(parse_collages(tree))
            if tree.find_class('pager_next'):
                data['page'] += 1
            else:
                break
        return collages