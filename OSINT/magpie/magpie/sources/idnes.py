import re
import urllib.parse

from bs4 import BeautifulSoup

from ..models import Listing
from ..text import fees_from_text, parse_price
from .base import Source

DEFAULT_URL = "https://reality.idnes.cz/s/pronajem/byty/do-14000-za-mesic/brno-mesto/"
FEE_ROW_RE = re.compile(r"poplat|služb|energi|náklad|inkas", re.I)


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


class Idnes(Source):
    """reality.idnes.cz search results (server-rendered HTML, allowed by robots.txt)."""

    name = "idnes"

    def fetch(self):
        url = self.opts.get("url", DEFAULT_URL)
        pages = self.opts.get("pages", 3)
        listings, seen = [], set()
        for page in range(pages):  # iDNES counts pages from 0; the first has no parameter
            page_url = url if page == 0 else f"{url}{'&' if '?' in url else '?'}page={page}"
            try:
                found = self.parse_list(self.http.get(page_url).text, page_url)
            except Exception:
                if page == 0:
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
        for item in soup.select("div.c-products__item"):
            link = item.select_one("a.c-products__link[href]")
            if not link:
                continue  # ad slot
            href = urllib.parse.urljoin(base_url, link["href"])
            m = re.search(r"/([0-9a-f]{16,})/?$", href)
            if not m:
                continue
            title = _clean(item.select_one(".c-products__title").get_text(" "))
            info = item.select_one(".c-products__info")
            price = item.select_one(".c-products__price")
            img = item.select_one("img[data-src]")
            out.append(Listing(
                source=self.name,
                id=m.group(1),
                url=href,
                title=title[:1].upper() + title[1:],
                rent=parse_price(price.get_text(" ")) if price else None,
                locality=_clean(info.get_text(" ")) if info else "",
                image=img["data-src"] if img else None,
            ))
        return out

    def enrich(self, listing):
        self.parse_detail(self.http.get(listing.url).text, listing)

    def parse_detail(self, html, listing):
        soup = BeautifulSoup(html, "html.parser")
        desc = soup.select_one(".b-desc")
        listing.description = _clean(desc.get_text(" ")) if desc else ""

        fees, note = 0, ""
        for dt in soup.select(".b-definition-columns dt"):
            dd = dt.find_next_sibling("dd")
            if not dd:
                continue
            label, value = _clean(dt.get_text(" ")), _clean(dd.get_text(" "))
            if label.lower().startswith("poznámka k ceně"):
                note = value
            elif FEE_ROW_RE.search(label) and "spotřeba" not in label.lower():
                amount = parse_price(value)
                if amount:
                    fees += amount
        if fees:
            listing.fees = fees
        elif note:
            amount, included = fees_from_text(note)
            listing.fees_included = included
            listing.fees = amount
