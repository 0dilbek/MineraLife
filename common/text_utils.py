import re

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_multiline_text(value):
    """Matndagi \\r\\n, \\r, \\n va boshqa boshqaruv belgilarini tozalaydi."""
    if value is None:
        return value
    if not isinstance(value, str):
        value = str(value)
    if not value:
        return value

    text = value.replace("\\r\\n", "\n").replace("\\r", "\n").replace("\\n", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS_RE.sub("", text)
    return text.strip()