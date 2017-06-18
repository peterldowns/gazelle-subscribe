#!/usr/bin/env python
# coding: utf-8
import json

from gazelle import Session


HOST = 'redacted.ch'
CREDENTIALS_FILENAME = 'credentials.json'
DUMP_FILENAME = 'collages.jsonlines'
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


def to_mapping(collage_list):
    return {c['id']: c for c in collage_list}


def diff_collage_lists(old, new):
    m_old = to_mapping(old)
    m_new = to_mapping(new)
    ids_old = set(m_old.keys())
    ids_new = set(m_new.keys())
    added = [m_new[i] for i in (ids_new - ids_old)]
    removed = [m_old[i] for i in (ids_old - ids_new)]
    modified = []
    for i in (ids_old & ids_new):
        for key in ['updated', 'torrents']:
            if m_new[i][key] != m_old[i][key]:
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
        print('--  {} :: {} ({})'.format(s.url(collage['url']), collage['name'], collage['updated']))

    for key in diff.keys():
        print('{} collages have been {}:'.format(len(diff[key]), key))
        for collage in diff[key]:
            print_collage(collage)
    print('Done.\n')


def main():
    s = Session(HOST)
    credentials = parse_credentials()
    if not s.login(**credentials):
        raise Exception("Could not log in.")
    new_collages = list(s.bookmarked_collages())
    old_collages = list(read_dump())
    diff = diff_collage_lists(old_collages, new_collages)
    alert(s, diff)
    write_diff(diff)
    write_dump(new_collages)


if __name__ == '__main__':
    main()
