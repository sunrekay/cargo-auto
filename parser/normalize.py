"""Turn the site's display strings into numbers fit for analysis.

Raw text is always kept alongside, so a parsing miss never destroys data.
"""
import re

CURRENCY = {"¥": "CNY", "￥": "CNY", "$": "USD", "€": "EUR", "£": "GBP", "rmb": "CNY",
            "cny": "CNY", "usd": "USD", "eur": "EUR"}
# Chinese listings price in 万 (10k) — common on guazi even in the English UI
WAN = ("万", "wan")


def _num(s: str) -> float | None:
    m = re.search(r"\d[\d,\s]*(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "").replace(" ", ""))
    except ValueError:
        return None


def price(raw: str | None) -> tuple[float | None, str | None]:
    """(amount, ISO currency) from e.g. '¥ 59,800', '5.98万', 'USD 12,300'."""
    if not raw:
        return None, None
    low = raw.lower()
    cur = next((c for sym, c in CURRENCY.items() if sym in low), None)
    val = _num(raw)
    if val is None:
        return None, cur
    if any(w in low for w in WAN):
        val *= 10_000
        cur = cur or "CNY"
    return round(val, 2), cur


def mileage_km(raw: str | None) -> float | None:
    """Kilometres from '12,345 km', '1.2万公里', '8,000 miles'."""
    if not raw:
        return None
    low = raw.lower()
    val = _num(raw)
    if val is None:
        return None
    if any(w in low for w in WAN):
        val *= 10_000
    if "mile" in low or "mi." in low:
        val *= 1.609344
    return round(val, 1)


def year(raw: str | None) -> int | None:
    """A plausible model year out of '2019', '2019-07', 'Jul 2019'."""
    if not raw:
        return None
    for m in re.finditer(r"(19|20)\d{2}", raw):
        y = int(m.group(0))
        if 1950 <= y <= 2100:
            return y
    return None
