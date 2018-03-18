import re
import string
import sys
from bs4 import BeautifulSoup
from colorama import Fore
from requests import RequestException

from dirhunt.colors import status_code_colors
from dirhunt.utils import colored, remove_ansi_escape

MAX_RESPONSE_SIZE = 1024 * 512
TIMEOUT = 10


def sizeof_fmt(num, suffix='B'):
    if num is None:
        return '???'
    if isinstance(num, str):
        num = int(num)
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%d%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%d%s%s" % (num, 'Yi', suffix)


class UrlInfo(object):
    _data = None
    _url_info = None

    def __init__(self, sessions, url):
        self.sessions = sessions
        self.url = url

    def get_data(self):
        session = self.sessions.get_session()
        try:
            resp = session.get(self.url.url, stream=True, timeout=TIMEOUT, allow_redirects=False)
        except RequestException:
            return
        try:
            text = resp.raw.read(MAX_RESPONSE_SIZE, decode_content=True)
        except RequestException:
            return
        try:
            soup = BeautifulSoup(text, 'html.parser')
        except NotImplementedError:
            soup = title = body = None
        else:
            title = soup.select_one('title')
            if title:
                title = title.string
            body = soup.select_one('body')
            if body:
                body = str(body)
        if sys.version_info >= (3,):
            text = text.decode('utf-8', errors='ignore')
        return {
            'resp': resp,
            'text': text,
            'soup': soup,
            'title': title,
            'body': body,
        }

    @property
    def data(self):
        if self._data is None:
            self._data = self.get_data()
        return self._data

    def get_url_info(self):
        size = self.data['resp'].headers.get('Content-Length')
        size = len(self.data.get('text', '')) if size is None else size
        status_code = int(self.data['resp'].status_code)
        out = colored('({})'.format(status_code), status_code_colors(status_code)) + " "
        out += colored('({:>6})'.format(sizeof_fmt(size)), Fore.LIGHTYELLOW_EX) + " "
        return out

    @property
    def url_info(self):
        if self._url_info is None:
            self._url_info = self.get_url_info()
        return self._url_info

    def text(self):
        text = self.data['title'] or self.data['body'] or self.data['text'] or ''
        text = re.sub('[{}]'.format(string.whitespace), ' ', text)
        return re.sub(' +', ' ', text)

    def line(self, line_size, url_column):
        if len(self.url_info) + url_column + 20 < line_size:
            return self.one_line(line_size, url_column)
        else:
            return self.multi_line(line_size)

    def one_line(self, line_size, url_column):
        text = self.text()[:line_size-url_column-len(list(remove_ansi_escape(self.url_info)))-3]
        out = self.url_info
        out += colored(('{:<%d}' % url_column).format(self.url.url), Fore.LIGHTBLUE_EX) + "  "
        out += text
        return out

    def multi_line(self, line_size):
        out = colored('┏', Fore.LIGHTBLUE_EX) + ' {} {}\n'.format(
            self.url_info, colored(self.url.url, Fore.LIGHTBLUE_EX)
        )
        out += colored('┗', Fore.LIGHTBLUE_EX) + ' {}'.format(self.text()[:line_size-2])
        return out
