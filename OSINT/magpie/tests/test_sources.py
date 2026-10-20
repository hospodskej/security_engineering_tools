import os

from magpie.http import Robots
from magpie.models import Listing
from magpie.sources.bazos import Bazos
from magpie.sources.idnes import Idnes
from magpie.sources.realitymix import Realitymix

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name, mode="r"):
    with open(os.path.join(FIX, name), mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def test_idnes_list_and_detail():
    listings = Idnes(None, {}).parse_list(fixture("idnes_list.html"), "https://reality.idnes.cz/s/")
    by_street = {l.locality.split(",")[0]: l for l in listings}
    assert set(by_street) == {"Hoppova", "Tkalcovská", "Petra Křivky"}  # the ad slot is skipped
    hoppova = by_street["Hoppova"]
    assert hoppova.rent == 13500 and hoppova.locality == "Hoppova, Brno - Veveří"
    assert hoppova.title == "Pronájem bytu 1+kk 23 m²"
    assert hoppova.id == "6ace0a21a3b106bb48019a51"

    detail = Listing("idnes", "x", "u", "Pronájem bytu 1+kk 32 m²", 13500, locality="Tkalcovská, Brno - Zábrdovice")
    Idnes(None, {}).parse_detail(fixture("idnes_detail.html"), detail)
    assert "Služby činí" in detail.description


def test_realitymix_list_and_detail():
    listings = Realitymix(None, {}).parse_list(fixture("realitymix_list.html"), "https://realitymix.cz/")
    by_id = {l.id: l for l in listings}
    assert by_id["8727033"].rent == 14000
    assert by_id["8727033"].locality == "Součkova, Brno-Komín, Brno"
    assert by_id["8727033"].title == "Pronájem bytu, 1+kk, 23 m²"
    assert all(l.image is None or l.image.startswith("https://") for l in listings)

    detail = Listing("realitymix", "8724243", "u", "Pronájem bytu, 2+kk, 40 m²", 15900)
    Realitymix(None, {}).parse_detail(fixture("realitymix_detail.html"), detail)
    assert (round(detail.lat, 3), round(detail.lon, 3)) == (49.167, 16.551)
    assert detail.description.startswith("Pronájem bytu 2+kk")


def test_bazos_rss_and_detail():
    listings = Bazos(None, {}).parse_rss(fixture("bazos_rss.xml", "rb"))
    by_id = {l.id: l for l in listings}
    item = by_id["225343235"]
    assert item.title == "Pronájem bytu 2+kk s balkonem, Podnásepní" and item.rent == 20000
    assert item.locality == ""  # only the detail page says where it is
    assert by_id["225343171"].rent is None  # "V textu"

    detail = Listing("bazos", "225290633", "u", "Pronájem bytu 2+kk, 32 m², Brno - Cejl", 14500)
    Bazos(None, {}).parse_detail(fixture("bazos_detail.html"), detail)
    assert detail.locality == "Brno 602 00"
    assert detail.rent == 14500
    assert detail.description.startswith("Naše realitní kancelář")


def test_robots_wildcards_and_longest_match():
    bazos = Robots("User-agent: *\nDisallow: /*hlokalita=\nDisallow: /*cenado=\n\nUser-agent: BLEXBot\nDisallow: /\n")
    assert bazos.allowed("https://www.bazos.cz/rss.php?rub=re&cat=65&typ=3")
    assert not bazos.allowed("https://reality.bazos.cz/pronajmu/byt/?hlokalita=61600&humkreis=8")

    sreality = Robots("User-agent: *\nDisallow: /\n\nUser-agent: Googlebot\nAllow: /\n")
    assert not sreality.allowed("https://www.sreality.cz/hledani/pronajem/byty/brno")

    idnes = Robots("User-agent: *\nAllow: /\nDisallow: /s/*page=*sort=\nDisallow: /s/*/do-*sort=\n")
    assert idnes.allowed("https://reality.idnes.cz/s/pronajem/byty/do-14000-za-mesic/brno-mesto/?page=1")
    assert not idnes.allowed("https://reality.idnes.cz/s/pronajem/byty/do-14000-za-mesic/brno-mesto/?page=1&sort=x")

    bezrealitky = Robots("User-agent: *\nDisallow: /vyhledat*\n")
    assert not bezrealitky.allowed("https://www.bezrealitky.cz/vyhledat?offerType=PRONAJEM")
    assert bezrealitky.allowed("https://www.bezrealitky.cz/nemovitosti-byty-domy/1-x")
