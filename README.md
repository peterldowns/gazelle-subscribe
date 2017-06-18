# gazelle-subscribe
Use this to check if any of your bookmarked collages have been updated since you last checked. Will nicely print out the added, removed, and modified collages, as well as the torrents that were added or removed.

### install
Requires Python 3 (has only been tested against 3.6.1).

```bash
pip install -r requirements.txt
```

### configure

```bash
echo '{"username": "my-username", "password": "my-password"}' > credentials.json
```

There are some global variables at the top of `differ.py` that you can modify to choose the gazelle host, as well as some of the local filenames (if for some reason you want to put the script output in a specific place.)

### run
```bash
$ ./differ.py
```

outputs something like:

```
updating 1 items
.
0 collages have been removed:
1 collages have been added:
-- https://redacted.ch/collages.php?id=399 :: Pitchfork Perfect 10s (jun 04 2017, 19:27)
0 collages have been modified:
Done.
```
