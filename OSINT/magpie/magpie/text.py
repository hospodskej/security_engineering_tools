import re
import unicodedata


def normalize(text):
    """Lowercase, strip diacritics and collapse punctuation so 'Brno-Žabovřesky' == 'brno zabovresky'."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^\w+]+", " ", text)
    return text.strip()


def contains_phrase(text, phrase):
    """Whole-word match of a phrase inside already-normalized text."""
    phrase = normalize(phrase)
    return bool(phrase) and re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def parse_price(text):
    """'13 500 Kč', '13.500,-', '13500 CZK/měsíc' -> 13500. Returns None if there is no number."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return int(text)
    text = re.sub(r"[​-‍⁠﻿]", "", text)  # iDNES puts zero-width joiners in prices
    text = text.replace("\xa0", " ").replace(" ", " ")
    m = re.search(r"\d{1,3}(?:[ .]\d{3})+|\d+", text)
    if not m:
        return None
    return int(re.sub(r"\D", "", m.group(0)))


_STOP = r"kauc|vratn|proviz|jistin|depozit|najemne|najem\b|najmu\b|cena\b|osob"
_FEE_WORDS = r"poplat|zaloh|sluzb|energi|naklad|inkas"
_AMOUNT = r"(\d{1,2}(?:[ .]\d{3})|\d{3,5})\s*(?:,\s*-+|,00|\.-+)?\s*(?:kc|czk|korun|,-|-)"

# A fee word, then (without crossing a sentence or a deposit/rent mention) an amount.
_FEE_RE = re.compile(
    rf"\b(?:{_FEE_WORDS})\w*(?:(?!{_STOP}|\.\s)[^;\n]){{0,45}}?{_AMOUNT}"
)
_INCLUDED_RE = re.compile(
    r"(?:vcetne|vc|vcet|vc\.)\s+(?:vsech\s+)?(?:poplatk|energi|sluzeb|zaloh)"
    r"|(?:poplatky|energie|sluzby|zalohy)\s+(?:jsou\s+)?(?:v\s+cene|zahrnut)"
    r"|cena\s+(?:je\s+)?(?:konecna|vcetne)"
)
_EXCLUDED_RE = re.compile(r"\b(?:bez|neni\s+vcetne|nezahrnuje)\s+(?:poplatk|energi|sluzeb|zaloh)")


def fees_from_text(text):
    """Best-effort read of monthly fees from a listing description.

    Returns (fees, included): fees in CZK or None, and whether the text says the
    rent already includes them. Anything implausible is treated as unknown, so a
    misread can only cause an extra alert, never a missed one.
    """
    raw = (text or "").replace("\xa0", " ")
    norm = unicodedata.normalize("NFKD", raw)
    norm = "".join(c for c in norm if not unicodedata.combining(c)).lower()
    norm = re.sub(r"[ \t]+", " ", norm)

    if _INCLUDED_RE.search(norm) and not _EXCLUDED_RE.search(norm):
        return None, True

    amounts = [int(re.sub(r"\D", "", m.group(1))) for m in _FEE_RE.finditer(norm)]
    amounts = list(dict.fromkeys(a for a in amounts if 200 <= a <= 9000))
    if len(amounts) == 1:
        return amounts[0], False
    # Several amounts: accept one only if it is clearly the total of the others
    # ("poplatky 3 000 Kč: voda 1 000, teplo 1 200, ..."). Anything else is ambiguous,
    # and guessing high could hide a flat that is actually in budget.
    for a in amounts:
        rest = sum(amounts) - a
        if rest and abs(a - rest) <= 0.1 * a:
            return a, False
    return None, False
