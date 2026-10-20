import re
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from ..models import Listing
from ..text import parse_price
from .base import Source

# Bazoš' robots.txt forbids its search/location filters, but not the category RSS
# feed: newest flat-rental ads nationwide, about two hours' worth per fetch.
DEFAULT_URL = "https://www.bazos.cz/rss.php?rub=re&cat=65&typ=3"


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


class Bazos(Source):
    name = "bazos"

    def fetch(self):
        return self.parse_rss(self.http.get(self.opts.get("url", DEFAULT_URL)).content)

    def parse_rss(self, xml):
        out = []
        for item in ET.fromstring(xml).iter("item"):
            link = _clean(item.findtext("link"))
            m = re.search(r"/inzerat/(\d+)/", link)
            if not m:
                continue
            raw_title = _clean(item.findtext("title"))
            title, _, price = raw_title.rpartition(": ")
            if not title:
                title, price = raw_title, ""
            desc_html = item.findtext("description") or ""
            soup = BeautifulSoup(desc_html, "html.parser")
            img = soup.select_one("img[src]")
            out.append(Listing(
                source=self.name,
                id=m.group(1),
                url=link,
                title=title,
                rent=parse_price(price),
                description=_clean(soup.get_text(" ")),
                image=img["src"] if img else None,
            ))
        return out

    def enrich(self, listing):
        self.parse_detail(self.http.get(listing.url).text, listing)

    def parse_detail(self, html, listing):
        soup = BeautifulSoup(html, "html.parser")
        desc = soup.select_one("div.popisdetail")
        if desc:
            listing.description = _clean(desc.get_text(" "))
        for td in soup.find_all("td"):
            if _clean(td.get_text()) == "Lokalita:":
                # The next cell is a map icon; the postcode and town follow it.
                loc = _clean(" ".join(c.get_text(" ") for c in td.find_next_siblings("td")))
                # "602 00 Brno" -> "Brno 602 00": town first, like the other sites
                m = re.match(r"(\d{3} ?\d{2})\s+(.*)", loc)
                listing.locality = f"{m.group(2)} {m.group(1)}" if m else loc
                break
        price = None
        for td in soup.find_all("td"):
            if _clean(td.get_text()) == "Cena:":
                value = td.find_next_sibling("td")
                price = parse_price(value.get_text(" ")) if value else None
                break
        if price:
            listing.rent = price
