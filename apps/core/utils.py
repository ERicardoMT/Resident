import re

import bleach

_KG_PATTERN = re.compile(
    r"(\d(?:[\d.,]*))\s*kg\b",
    re.IGNORECASE,
)

_ALLOWED_CATALOG_TAGS = {
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "ul",
    "ol",
    "li",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "a",
    "h2",
    "h3",
    "h4",
    "blockquote",
}


_ALLOWED_CATALOG_ATTRIBUTES = {
    "a": [
        "href",
        "target",
        "rel",
    ],
    "th": [
        "colspan",
        "rowspan",
    ],
    "td": [
        "colspan",
        "rowspan",
    ],
}


_ALLOWED_CATALOG_PROTOCOLS = {
    "http",
    "https",
    "mailto",
}


def sanitize_catalog_html(value):
    """
    Conserva únicamente el HTML necesario
    para las fichas técnicas del catálogo.
    """

    if value is None:
        return ""

    return bleach.clean(
        str(value),
        tags=_ALLOWED_CATALOG_TAGS,
        attributes=_ALLOWED_CATALOG_ATTRIBUTES,
        protocols=_ALLOWED_CATALOG_PROTOCOLS,
        strip=True,
    )

def normalize_kg_text(value):
    """
    Normaliza unidades de peso visibles:

    150 KG  -> 150 kg
    150 Kg  -> 150 kg
    150KG   -> 150 kg
    """

    if value is None:
        return ""

    return _KG_PATTERN.sub(
        r"\1 kg",
        str(value),
    )