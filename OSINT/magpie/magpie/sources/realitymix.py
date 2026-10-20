import re
import urllib.parse

from bs4 import BeautifulSoup

from ..models import Listing
from ..text import parse_price
from .base import Source

# Sorted newest first by default, so the first pages hold everything new.
DEFAULT_URL = "https://realitymix.cz/reality/byty/pronajem/jihomoravsky/brno-mesto"
FEE_LABEL_RE = re.compile(r"poplat|služb|energi|náklad|inkas", re.I)


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


class Realitymix(Source):
    name = "realitymix"

    def fetch(self):
        url = self.opts.get("url", DEFAULT_URL)
        pages = self.opts.get("pages", 2)
        listings, seen = [], set()
        for page in range(1, pages + 1):
            page_url = url if page == 1 else f"{url}{'&' if '?' in url else '?'}stranka={page}"
            try:
                found = self.parse_list(self.http.get(page_url).text, page_url)
            except Exception:
                if page == 1:
                    raise
                break  # keep what the earlier pages gave
            fresh = [l for l in found if l.id not in seen]
            if not fresh:
                break
            seen.update(l.id for l in fresh)
            listings.extend(fresh)
        return listings

    def parse_list(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for card in soup.select("div.advert-item__content"):
            link = card.select_one("h2 a[href]")
            if not link:
                continue
            href = urllib.parse.urljoin(base_url, link["href"])
            m = re.search(r"-(\d+)\.html$", href)
            if not m:
                continue
            loc = card.select_one("h2 + p")
            price = card.select_one("div.text-xl")
            img = card.select_one("img[src]")
            out.append(Listing(
                source=self.name,
                id=m.group(1),
                url=href,
                title=_clean(link.get_text(" ")),
                rent=parse_price(price.get_text(" ")) if price else None,
                locality=_clean(loc.get_text(" ")) if loc else "",
                image=img["src"].replace("http://", "https://", 1) if img else None,
            ))
        return out

    def enrich(self, listing):
        self.parse_detail(self.http.get(listing.url).text, listing)

    def parse_detail(self, html, listing):
        soup = BeautifulSoup(html, "html.parser")
        desc = soup.select_one(".advert-description")
        if desc:
            listing.description = _clean(desc.get_text(" ")).removeprefix("Popis nemovitosti ").strip()
        gps = soup.select_one("#map[data-gps-lat][data-gps-lon]")
        if gps:
            try:
                listing.lat, listing.lon = float(gps["data-gps-lat"]), float(gps["data-gps-lon"])
            except ValueError:
                pass
        fees = 0
        for li in soup.select("li"):
            label, sep, value = _clean(li.get_text(" ")).partition(":")
            if sep and len(label) < 40 and FEE_LABEL_RE.search(label):
                fees += parse_price(value) or 0
        if fees:
            listing.fees = fees
