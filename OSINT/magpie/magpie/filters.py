import re
import urllib.parse
from dataclasses import dataclass, field

from .text import contains_phrase, fees_from_text, normalize

MATCH, REJECT, UNKNOWN = "match", "reject", "unknown"

# Title patterns for a room in a shared flat rather than a whole flat. Only the
# title is checked: descriptions of whole flats often say "vhodné pro spolubydlení".
ROOM_TITLE_RE = re.compile(
    r"\bpokoj\w*\s+v\s+byt"
    r"|\b(?:pronajem|podnajem|nabizim|nabizime|volny|volne)\s+(?:\w+\s+)?pokoj"
    r"|^\s*pokoj\b"
    r"|\bspolubydl"
    r"|\bhledam\w*\s+spolubydl"
    r"|\bubytovn"
    r"|\blozk\w*\s+v\b"
)


@dataclass
class Verdict:
    ok: bool
    reason: str = ""
    flags: list[str] = field(default_factory=list)


def _point_in_polygon(lat, lon, polygon):
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


class Filters:
    def __init__(self, cfg):
        area = cfg.get("area", {})
        self.include = area.get("include", [])
        self.exclude = area.get("exclude", [])
        self.polygon = area.get("polygon") or []
        self.include_postcodes = {re.sub(r"\D", "", p) for p in area.get("include_postcodes", [])}
        self.exclude_postcodes = {re.sub(r"\D", "", p) for p in area.get("exclude_postcodes", [])}
        # Czech declines place names: "v Brně", "z Brna", "Brnem".
        self.city_forms = area.get("city_forms") or [area.get("city", "Brno")]
        self.notify_unknown_area = area.get("notify_unknown_area", True)

        price = cfg.get("price", {})
        self.max_total = price["max_total"]
        self.max_fee_guess = price.get("max_fee_from_text", 9000)

        rooms = cfg.get("rooms", {})
        self.exclude_title_words = [normalize(w) for w in rooms.get("exclude_title_words", [])]

    # --- area -------------------------------------------------------------
    def _names(self, text):
        norm = normalize(text)
        inc = any(contains_phrase(norm, n) for n in self.include)
        exc = any(contains_phrase(norm, n) for n in self.exclude)
        return inc, exc

    def area(self, listing, final=False):
        """MATCH / REJECT / UNKNOWN. Before the detail page is fetched (final=False) only
        positive evidence of another place rejects; afterwards a listing must at least
        mention the city to count as UNKNOWN rather than elsewhere."""
        for text in (listing.locality, listing.title):
            inc, exc = self._names(text)
            if inc:
                return MATCH
            if exc:
                return REJECT

        if listing.lat is not None and listing.lon is not None and self.polygon:
            return MATCH if _point_in_polygon(listing.lat, listing.lon, self.polygon) else REJECT

        if final and listing.description:
            inc, exc = self._names(listing.description)
            if inc and not exc:
                return MATCH
            if exc and not inc:
                return REJECT

        codes = {a + b for a, b in re.findall(r"\b(\d{3}) ?(\d{2})\b", f"{listing.locality} {listing.title}")}
        if codes & self.include_postcodes:
            return MATCH
        if codes & self.exclude_postcodes:
            return REJECT

        if listing.locality:
            where = listing.locality
        elif not final:
            return UNKNOWN  # nothing known yet; the detail page will tell
        else:
            where = f"{listing.title} {listing.description}"
        norm = normalize(where)
        return UNKNOWN if any(contains_phrase(norm, form) for form in self.city_forms) else REJECT

    # --- rooms ------------------------------------------------------------
    def is_room(self, listing):
        if listing.is_room:
            return True
        title = normalize(listing.title)
        # URL slugs sometimes say what the title doesn't ("...-studentskeho-pokoje-brno-...").
        slug = normalize(urllib.parse.urlsplit(listing.url).path.rsplit("/", 1)[-1])
        if ROOM_TITLE_RE.search(title) or ROOM_TITLE_RE.search(slug):
            return True
        return any(contains_phrase(title, w) for w in self.exclude_title_words)

    # --- price ------------------------------------------------------------
    def apply_text_fees(self, listing):
        """Fill in fees from the description when the site has no structured value."""
        if listing.fees is not None or listing.fees_included or not listing.description:
            return
        fees, included = fees_from_text(listing.description)
        if included:
            listing.fees_included = True
        elif fees is not None and fees <= self.max_fee_guess and (listing.rent is None or fees < listing.rent):
            listing.fees = fees
            listing.notes.append("fees read from description")

    # --- verdicts -----------------------------------------------------------
    def precheck(self, listing):
        """Cheap checks on search-result data, before fetching the listing's detail page."""
        if listing.rent is None or listing.rent <= 0:
            return Verdict(False, "no price")
        if listing.rent > self.max_total:
            return Verdict(False, f"rent {listing.rent} over budget")
        if listing.total is not None and listing.total > self.max_total:
            return Verdict(False, f"total {listing.total} over budget")
        if self.is_room(listing):
            return Verdict(False, "room / shared flat")
        if self.area(listing) == REJECT:
            return Verdict(False, f"area: {listing.locality or listing.title}")
        return Verdict(True)

    def final(self, listing):
        """Full decision once the detail page (description, fees) has been merged in."""
        pre = self.precheck(listing)
        if not pre.ok:
            return pre
        self.apply_text_fees(listing)
        flags = []
        total = listing.total
        if total is None:
            flags.append("fees not listed")
        elif total > self.max_total:
            return Verdict(False, f"total {total} over budget")

        area = self.area(listing, final=True)
        if area == REJECT:
            return Verdict(False, f"area: {listing.locality or listing.title}")
        if area == UNKNOWN:
            if not self.notify_unknown_area:
                return Verdict(False, "area unclear")
            flags.append("area unclear")
        return Verdict(True, flags=flags)
