# coding: utf-8
import re
import json
import time

def read_dump(filename):
    try:
        lines = open(filename).readlines()
    except Exception as e:
        lines = []
    yield from map(json.loads, lines)


def write_dump(filename, collages):
    with open(filename, 'w') as fout:
        for c in collages:
            json.dump(c, fout, sort_keys=True)
            fout.write('\n')
        fout.flush()
        fout.close()


def write_diff(filename, diff):
    with open(filename, 'w') as fout:
        json.dump(diff, fout, indent=2, sort_keys=True)


def parse_credentials(filename):
    credentials = json.load(open(filename))
    assert credentials.get('username')
    assert credentials.get('password')
    return credentials


def to_mapping(l, k='id'):
    return {c[k]: c for c in l}


def to_number(s):
    return int(re.sub(r'[^\d]', '', s))


def timeout_consume(timeout_seconds, callback, items, dt=0.1):
    for i in items:
        tick = time.time()
        yield callback(i)
        elapsed = time.time() - tick
        if elapsed < timeout_seconds:
            time.sleep(timeout_seconds - elapsed)
