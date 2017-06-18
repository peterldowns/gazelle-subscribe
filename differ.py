#!/usr/bin/env python
# coding: utf-8
import lxml.html
import sys
import urllib.parse as urlparse

import utils
from gazelle import Session


# The website you're checking
HOST = 'redacted.ch'
# {"username": "xxx", "password": "yyy"}
CREDENTIALS_FILENAME = 'credentials.json'
# Filename to store the collage / torrent information for future comparison.
DUMP_FILENAME = 'collages.jsonlines'
# Filename to store the last-calculated diff.
DIFF_FILENAME = 'diff.json'
# You're sure you don't have more pages of bookmarks than this. Only useful to
# make sure that this script eventually executes in the case of an unforeseen
# bug.
MAX_PAGES = 100


def get_bookmarked_collages(s, max_pages=MAX_PAGES):
    data = {'type': 'collages', 'page': 1}
    while True:
        r = s.get(s.url('bookmarks.php'), params=data)
        if not r.status_code == 200:
            return
        tree = lxml.html.fromstring(r.content)
        yield from parse_collages(tree)
        if tree.find_class('pager_next') and data['page'] < max_pages:
            data['page'] += 1
        else:
            break


def parse_collages(tree):
    table = tree.find_class('collage_table')
    if not len(table):
        raise Exception('could not find collage table')
    table = table[0]
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
        collage['num_torrents'] = utils.to_number(columns[2].text_content())
        collage['num_subscribers'] = utils.to_number(columns[3].text_content())
        update_str = columns[4].find('span').attrib['title']
        # Can be parsed with
        #   datetime.strptime(update_str, '%b %d %Y, %H:%M')
        # but then can't dump to JSON, so leaving as string like this.
        collage['updated'] = update_str.strip().lower()
        yield collage


def torrent_adder(s):
    def add_torrents(collage):
        r = s.collage(collage['id'])
        if not r.status_code == 200:
            raise Exception('Could not fetch collage details', collage)
        data = r.json()
        if not data['status'] == 'success':
            raise Exception('Bad API response', data)
        # Each torrent has the following keys:
        # id, name, year, categoryId, recordLabel, catalogueNumber, vanityHouse,
        # tagList, releaseType, wikiImage, msuicInfo, torrents
        data = data['response']
        collage['torrents'] = data['torrentgroups']
    return add_torrents


def diff_torrent_lists(old, new):
    m_old = utils.to_mapping(old)
    m_new = utils.to_mapping(new)
    ids_old = set(m_old.keys())
    ids_new = set(m_new.keys())
    added = [m_new[i] for i in (ids_new - ids_old)]
    removed = [m_old[i] for i in (ids_old - ids_new)]
    return {
        'added': added,
        'removed': removed,
    }


def diff_collage_lists(old, new):
    m_old = utils.to_mapping(old)
    m_new = utils.to_mapping(new)
    ids_old = set(m_old.keys())
    ids_new = set(m_new.keys())
    added = [m_new[i] for i in (ids_new - ids_old)]
    removed = [m_old[i] for i in (ids_old - ids_new)]
    modified = []
    for i in (ids_old & ids_new):
        updated = False
        for key in ['updated', 'num_torrents']:
            if m_new[i][key] != m_old[i][key]:
                updated = True
        if not updated:
            continue
        modified.append({
            'old': m_old[i],
            'new': m_new[i],
        })
    return {
        'added': added,
        'removed': removed,
        'modified': modified,
    }


def print_diff(s, diff):
    def print_collage(collage):
        print('-- {} :: {} ({})'.format(s.url(collage['url']), collage['name'], collage['updated']))

    def print_torrent(t, prefix):
        print('     {} {} :: {} - {} ({})'.format(
                prefix,
                s.url('/torrents.php?id=%s' % t['id']),
                t['name'],
                ','.join(a['name'] for a in t['musicInfo']['artists']),
                t['year']))

    for key in ['removed', 'added']:
        print('{} collages have been {}:'.format(len(diff[key]), key))
        for collage in diff[key]:
            print_collage(collage)
    print('{} collages have been modified:'.format(len(diff['modified'])))
    for m in diff['modified']:
        old = m['old']
        new = m['new']
        print_collage(new)
        torrents_diff = diff_torrent_lists(
                old.get('torrents', []), new.get('torrents', []))
        print('')
        for t in torrents_diff['removed']:
            # id, name, year, categoryId, recordLabel, catalogueNumber, vanityHouse,
            # tagList, releaseType, wikiImage, msuicInfo, torrents
            print_torrent(t, '-')
        for t in torrents_diff['added']:
            print_torrent(t, '+')
        print('')
    print('Done.\n')


def main():
    s = Session(HOST)
    credentials = utils.parse_credentials(CREDENTIALS_FILENAME)
    if not s.login(**credentials):
        raise Exception("Could not log in.")
    new_collages = list(get_bookmarked_collages(s))
    old_collages = list(utils.read_dump(DUMP_FILENAME))
    # Figure out which collages have changed since last time.
    diff = diff_collage_lists(old_collages, new_collages)

    # Keep track of the torrents in each collage. Update the "new" version of
    # each of these.
    to_update = [d['new'] for d in diff['modified']] + diff['added']
    print('updating %d items' % len(to_update))
    for _ in utils.timeout_consume(3.0, torrent_adder(s), to_update):
        sys.stdout.write('.')
        sys.stdout.flush()
    sys.stdout.write('\n')

    # Display the diff to the user.
    print_diff(s, diff)

    # Write the latest diff and dump the latest information for future
    # comparison.
    utils.write_diff(DIFF_FILENAME, diff)
    utils.write_dump(DUMP_FILENAME, new_collages)


if __name__ == '__main__':
    main()
