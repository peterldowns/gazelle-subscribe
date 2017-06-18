#!/usr/bin/env python
# coding: utf-8
import json
import sys
import time

from gazelle import Session

# The website you're checking
HOST = 'redacted.ch'
# {"username": "xxx", "password": "yyy"}
CREDENTIALS_FILENAME = 'credentials.json'
# Filename to store the collage / torrent information for future comparison.
DUMP_FILENAME = 'collages.jsonlines'
# Filename to store the last-calculated diff.
DIFF_FILENAME = 'diff.json'


def read_dump():
    try:
        lines = open(DUMP_FILENAME).readlines()
    except Exception as e:
        lines = []
    yield from map(json.loads, lines)


def write_dump(collages):
    with open(DUMP_FILENAME, 'w') as fout:
        for c in collages:
            json.dump(c, fout, sort_keys=True)
            fout.write('\n')
        fout.flush()
        fout.close()


def write_diff(diff):
    with open(DIFF_FILENAME, 'w') as fout:
        json.dump(diff, fout, indent=2, sort_keys=True)


def parse_credentials():
    credentials = json.load(open(CREDENTIALS_FILENAME))
    assert credentials.get('username')
    assert credentials.get('password')
    return credentials


def to_mapping(l):
    return {c['id']: c for c in l}


def diff_torrent_lists(old, new):
    m_old = to_mapping(old)
    m_new = to_mapping(new)
    ids_old = set(m_old.keys())
    ids_new = set(m_new.keys())
    added = [m_new[i] for i in (ids_new - ids_old)]
    removed = [m_old[i] for i in (ids_old - ids_new)]
    return {
        'added': added,
        'removed': removed,
    }


def diff_collage_lists(old, new):
    m_old = to_mapping(old)
    m_new = to_mapping(new)
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


def alert(s, diff):
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


def timeout_consume(timeout_seconds, callback, items, dt=0.1):
    for i in items:
        tick = time.time()
        yield callback(i)
        elapsed = time.time() - tick
        if elapsed < timeout_seconds:
            time.sleep(timeout_seconds - elapsed)


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


def main():
    s = Session(HOST)
    credentials = parse_credentials()
    if not s.login(**credentials):
        raise Exception("Could not log in.")
    new_collages = list(s.bookmarked_collages())
    old_collages = list(read_dump())
    # Figure out which collages have changed since last time.
    diff = diff_collage_lists(old_collages, new_collages)

    # Keep track of the torrents in each collage. Update the "new" version of
    # each of these.
    to_update = [d['new'] for d in diff['modified']] + diff['added']
    print('updating %d items' % len(to_update))
    for _ in timeout_consume(3.0, torrent_adder(s), to_update):
        sys.stdout.write('.')
        sys.stdout.flush()
    sys.stdout.write('\n')

    # Display the diff to the user.
    alert(s, diff)

    # Write the latest diff and dump the latest information for future
    # comparison.
    write_diff(diff)
    write_dump(new_collages)


if __name__ == '__main__':
    main()
