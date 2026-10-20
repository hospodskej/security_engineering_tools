from magpie.text import contains_phrase, fees_from_text, normalize, parse_price


def test_parse_price_formats():
    assert parse_price("13‍ 450‍ Kč/měsíc") == 13450  # iDNES zero-width joiners
    assert parse_price("14 500 Kč") == 14500
    assert parse_price("13.500,- Kč") == 13500
    assert parse_price("Cena na vyžádání") is None
    assert parse_price(12000) == 12000


def test_normalize_and_phrase():
    text = normalize("Bratislavská, Brno - Zábrdovice")
    assert contains_phrase(text, "Zábrdovice")
    assert not contains_phrase(normalize("byt s komínem"), "Komín")
    assert contains_phrase(normalize("Lísky, Brno - Komín"), "Komín")


def test_fees_from_real_idnes_breakdown():
    # Real description: rent, then services as a total followed by its breakdown.
    text = ("Měsíční poplatky: Nájemné činí 13.500, - Kč měsíčně. Služby činí 2.998, - Kč měsíčně pro "
            "maximálně dvě osoby. Každá další osoba je zpoplatněna částkou 500 Kč měsíčně navíc. Částka "
            "za služby obsahuje: zálohu na elektřinu v bytě ve výši 1.600, - Kč, zálohu na vodné ve výši "
            "700, - Kč, zálohu na teplo ve výši 460, - Kč, zálohu na energie společných prostor ve výši 83, - Kč")
    assert fees_from_text(text) == (2998, False)


def test_fees_simple_and_included():
    assert fees_from_text("Nájem 11 000 Kč + poplatky 2 500 Kč měsíčně.") == (2500, False)
    assert fees_from_text("Cena 13 000 Kč včetně poplatků.") == (None, True)
    assert fees_from_text("Cena je uvedena bez poplatků.") == (None, False)
    assert fees_from_text("Poznámka: + Inkaso 5 100 Kč + provize RK + vratná kauce") == (5100, False)


def test_fees_never_take_deposit_or_ambiguous_sums():
    assert fees_from_text("Poplatky dle spotřeby, kauce 24 000 Kč.") == (None, False)
    # Two unrelated amounts with no total: unknown rather than a guess that could hide a flat.
    assert fees_from_text("Služby 1 500 Kč, energie 2 000 Kč.") == (None, False)
