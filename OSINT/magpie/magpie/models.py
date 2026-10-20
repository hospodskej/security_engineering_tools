import re
from dataclasses import dataclass, field


@dataclass
class Listing:
    source: str
    id: str
    url: str
    title: str
    rent: int | None
    fees: int | None = None          # monthly service/energy charges, if the site lists them
    fees_included: bool = False      # rent already covers fees ("vč. poplatků")
    locality: str = ""
    lat: float | None = None
    lon: float | None = None
    description: str = ""
    is_room: bool | None = None      # the site's own category says room / shared flat
    image: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def key(self):
        return f"{self.source}:{self.id}"

    @property
    def fingerprint(self):
        """Layout + size + rent, to spot the same flat advertised on several sites."""
        disp = re.search(r"(\d)\s*\+\s*(kk|\d)", self.title, re.I)
        size = re.search(r"(\d{2,3})(?:[.,]\d+)?\s*m(?:2|²|\b)", self.title)
        if not (disp and size and self.rent):
            return None
        return f"{disp.group(1)}+{disp.group(2).lower()}|{size.group(1)}|{self.rent}"

    @property
    def total(self):
        if self.rent is None:
            return None
        if self.fees_included:
            return self.rent
        if self.fees is None:
            return None
        return self.rent + self.fees
