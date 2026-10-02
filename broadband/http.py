"""Small HTTP helpers (stdlib only), including a seekable file over HTTP Range."""
import io
import json
import shutil
import tempfile
import time
import urllib.error
import urllib.request

UA = "bsd-broadband-tracker (+https://github.com/edwardhrice/bsdfttpbroadband)"


def _open(url, headers=None, timeout=60, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))


def get_json(url):
    with _open(url) as r:
        return json.load(r)


class RangeFile(io.RawIOBase):
    """Read-only seekable file backed by HTTP Range requests.

    Lets zipfile read the central directory and a single member without
    downloading the whole archive.
    """

    BLOCK = 1 << 20

    def __init__(self, url):
        self.url = url
        self.pos = 0
        self._cache_start = 0
        self._cache = b""
        with _open(url, {"Range": "bytes=0-0"}) as r:
            if r.status != 206:
                raise OSError("server does not support Range requests")
            self.size = int(r.headers["Content-Range"].rsplit("/", 1)[1])
        self.url = r.geturl()  # follow redirects once

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        else:
            self.pos = self.size + offset
        return self.pos

    def _fetch(self, start, length):
        end = min(start + length, self.size) - 1
        with _open(self.url, {"Range": f"bytes={start}-{end}"}, timeout=120) as r:
            return r.read()

    def readinto(self, b):
        want = min(len(b), self.size - self.pos)
        if want <= 0:
            return 0
        lo, hi = self._cache_start, self._cache_start + len(self._cache)
        if not (lo <= self.pos and self.pos + want <= hi):
            self._cache_start = self.pos
            self._cache = self._fetch(self.pos, max(want, self.BLOCK))
            lo = self._cache_start
        off = self.pos - lo
        chunk = self._cache[off:off + want]
        b[:len(chunk)] = chunk
        self.pos += len(chunk)
        return len(chunk)


def download_to_tempfile(url):
    """Fallback when Range isn't supported: download the whole file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".zip")
    with _open(url, timeout=120) as r:
        shutil.copyfileobj(r, tmp, 1 << 20)
    tmp.seek(0)
    return tmp


def open_zip_source(url):
    """Return a seekable binary file for the zip at `url` (URL or local path)."""
    if not url.startswith(("http://", "https://")):
        return open(url, "rb")
    try:
        return RangeFile(url)
    except (OSError, KeyError, ValueError):
        return download_to_tempfile(url)
