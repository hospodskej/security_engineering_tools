import re
import time
import urllib.parse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


class Robots:
    """robots.txt rules for the '*' user agent, with RFC 9309 wildcards and longest-match wins.

    (urllib.robotparser treats '*' and '$' literally, which misreads most real-world files.)
    """

    def __init__(self, text):
        self.rules = []
        agents, in_rules = [], False
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = (p.strip() for p in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if in_rules:
                    agents, in_rules = [], False
                agents.append(value.lower())
            elif key in ("allow", "disallow"):
                in_rules = True
                if "*" in agents and value:
                    self.rules.append((key == "allow", value, self._compile(value)))

    @staticmethod
    def _compile(pattern):
        anchored = pattern.endswith("$")
        body = re.escape(pattern.rstrip("$")).replace(r"\*", ".*")
        return re.compile(body + ("$" if anchored else ""))

    def allowed(self, url):
        parts = urllib.parse.urlsplit(url)
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        best = None
        for allow, pattern, rx in self.rules:
            if rx.match(path):
                rank = (len(pattern), allow)
                if best is None or rank > best:
                    best = rank
        return best is None or best[1]


class Http:
    """requests.Session with retries, a per-host delay and a robots.txt check."""

    def __init__(self, delay=2.0, timeout=30, respect_robots=True):
        self.delay = delay
        self.timeout = timeout
        self.respect_robots = respect_robots
        self._last = {}
        self._robots = {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "cs,en;q=0.8"})
        retry = Retry(total=3, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=None, respect_retry_after_header=True)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def allowed(self, url):
        if not self.respect_robots:
            return True
        parts = urllib.parse.urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            try:
                resp = self.session.get(f"{base}/robots.txt", timeout=self.timeout)
                # RFC 9309: a missing robots.txt (4xx) means everything is allowed.
                text = resp.text if resp.ok else ""
                if resp.status_code >= 500:
                    text = "User-agent: *\nDisallow: /"
            except requests.RequestException:
                text = "User-agent: *\nDisallow: /"
            self._robots[base] = Robots(text)
        return self._robots[base].allowed(url)

    def _wait(self, url):
        host = urllib.parse.urlsplit(url).netloc
        elapsed = time.monotonic() - self._last.get(host, 0)
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last[host] = time.monotonic()

    def request(self, method, url, **kw):
        if not self.allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        self._wait(url)
        resp = self.session.request(method, url, timeout=self.timeout, **kw)
        resp.raise_for_status()
        return resp

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)
