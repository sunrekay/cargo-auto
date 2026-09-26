"""Harvest the car's full specification set from the page payload.

The rendered page shows roughly a dozen headline specs; the payload behind it
carries well over a hundred — VIN, body style, drive train, inspection grade,
registration dates, equipment lists — as arrays of {key, name, value}. Reading
them here is what makes "every characteristic on the page" actually true.
"""
from . import nextdata

# values that mean "not stated" rather than a real answer
EMPTY = {"", "-", "--", "null", "none", "n/a", "na", "unknown"}


def extract(html: str) -> dict[str, str]:
    """Every {name: value} specification pair the payload contains."""
    blob = nextdata.flight_blob(html)
    out: dict[str, str] = {}

    for arr in nextdata.iter_arrays(blob):
        head = arr[0]
        if not isinstance(head, dict) or not {"name", "value"} <= set(head):
            continue
        for item in arr:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            value = item.get("value")
            if isinstance(value, (list, dict)):
                continue
            value = str("" if value is None else value).strip()
            if not name or value.lower() in EMPTY or len(name) > 120:
                continue
            out.setdefault(name, value[:2000])

    return out
