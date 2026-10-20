import os

import pytest
import yaml

from magpie.filters import MATCH, REJECT, UNKNOWN, Filters
from magpie.models import Listing

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


@pytest.fixture(scope="module")
def filters():
    with open(CONFIG, encoding="utf-8") as f:
        return Filters(yaml.safe_load(f))


def make(**kw):
    base = dict(source="t", id="1", url="https://example.cz/detail/1", title="Pronájem bytu 1+kk 30 m²", rent=12000)
    base.update(kw)
    return Listing(**base)


@pytest.mark.parametrize("locality,expected", [
    ("Teyschlova, Brno - Bystrc", MATCH),            # iDNES
    ("Irkutská, Brno-Starý Lískovec, Brno", MATCH),  # Realitymix
    ("Bašty, Brno - Brno-město", MATCH),             # iDNES, historic centre
    ("Přízova, Brno-střed, Brno", MATCH),
    ("Kigginsova, Brno - Slatina", REJECT),
    ("Herčíkova, Brno - Královo Pole", REJECT),
    ("Ibsenova, Brno-sever, Brno", REJECT),
    ("Brno 641 00", MATCH),                          # Bazoš postcode, Žebětín
    ("Brno 614 00", REJECT),                         # Husovice
    ("Brno 602 00", UNKNOWN),                        # centre postcode, but shared with other areas
    ("Ostrava 708 00", REJECT),
])
def test_area(filters, locality, expected):
    assert filters.area(make(locality=locality), final=True) == expected


def test_area_gps_fallback(filters):
    assert filters.area(make(locality="Brno", lat=49.2306, lon=16.5256)) == MATCH   # by the dam
    assert filters.area(make(locality="Brno", lat=49.2050, lon=16.6900)) == REJECT  # Líšeň


def test_area_before_and_after_detail(filters):
    rss_item = make(title="Pronájem bytu 2+kk s balkonem, Podnásepní", locality="")
    assert filters.area(rss_item) == UNKNOWN              # fetch the detail page to find out
    assert filters.area(rss_item, final=True) == REJECT   # still nothing: not worth an alert


@pytest.mark.parametrize("title,url", [
    ("Pronájem pokoje 16 m²", "https://x.cz/detail/1"),
    ("Pronájem pokoje v bytě 3+1, Brno-Štýřice", "https://x.cz/detail/2"),
    ("Spolubydlení v centru", "https://x.cz/detail/3"),
    ("Pronájem bytu, 1+kk, 16 m²", "https://realitymix.cz/detail/brno/pronajem-studentskeho-pokoje-brno-1.html"),
    ("Hledáme pronájem", "https://x.cz/detail/4"),
])
def test_rooms_and_wanted_ads(filters, title, url):
    assert filters.is_room(make(title=title, url=url))


def test_whole_flat_suitable_for_flatmates_is_not_a_room(filters):
    assert not filters.is_room(make(title="Pronájem bytu 3+1, 75 m²", description="Vhodné i pro spolubydlení."))


def test_price_rules(filters):
    known = make(locality="Brno - Bystrc", rent=11000, fees=2500)
    assert filters.final(known).ok and filters.final(known).flags == []

    over = make(locality="Brno - Bystrc", rent=12000, fees=2500)
    assert not filters.final(over).ok

    unknown = make(locality="Brno - Bystrc", rent=13900)
    verdict = filters.final(unknown)
    assert verdict.ok and verdict.flags == ["fees not listed"]

    from_text = make(locality="Brno - Bystrc", rent=12000, description="Poplatky 3 000 Kč měsíčně.")
    assert not filters.final(from_text).ok
