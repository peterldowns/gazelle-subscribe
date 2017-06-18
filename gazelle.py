# coding: utf-8
import requests
import urllib.parse as urlparse

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
        self.hostname = 'https://{}'.format(hostname)

    def url(self, path):
        return urlparse.urljoin(self.hostname, path)

    def login(self, username, password):
        data = {'username': username, 'password': password}
        r = self.post(self.url('login.php'), data=data)
        return r.status_code == 200

    def collage(self, collage_id):
        data = {'action': 'collage', 'id': collage_id}
        return self.get(self.url('/ajax.php'), params=data)
