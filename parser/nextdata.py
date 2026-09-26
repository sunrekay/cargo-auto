"""Read the Next.js streamed data payload that this site renders from.

The visible DOM carries interface chrome and a fraction of the content; the
real record — full spec tables, the photo gallery — arrives as JSON pushed
into `self.__next_f`. These helpers reassemble that stream and walk the JSON
structures inside it without needing a full parse of the whole blob.
"""
import json
import re


def flight_blob(html: str) -> str:
    """Join the self.__next_f chunks back into one decoded string."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html, re.S)
    if not chunks:
        return html
    joined = "".join(chunks)
    try:
        return joined.encode("utf-8", "ignore").decode("unicode_escape", "ignore")
    except Exception:
        return joined


def _span(s: str, start: int, open_ch: str, close_ch: str) -> str | None:
    """The complete bracketed span beginning at s[start]."""
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return None


def json_array_at(s: str, start: int) -> str | None:
    return _span(s, start, "[", "]")


def iter_arrays(blob: str, *, min_len: int = 40, max_len: int = 400_000):
    """Every JSON array in the blob that parses, as Python lists."""
    for m in re.finditer(r"\[", blob):
        raw = json_array_at(blob, m.start())
        if not raw or not (min_len <= len(raw) <= max_len):
            continue
        try:
            value = json.loads(raw)
        except Exception:
            continue
        if isinstance(value, list) and value:
            yield value


def find_array(blob: str, key: str) -> list | None:
    """The array that follows "<key>": in the blob, parsed."""
    m = re.search(rf'"{re.escape(key)}"\s*:\s*\[', blob)
    if not m:
        return None
    raw = json_array_at(blob, m.end() - 1)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None
