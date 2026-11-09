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

# Las recomendaciones solo muestran modelos cuya capacidad
# no exceda demasiado la carga requerida por apoyo.
RECOMMENDATION_CAPACITY_RATIO = 3.0
RECOMMENDATION_MIN_RESULTS = 10


def select_close_capacity_products(
    products,
    required_load,
    limit,
    capacity_ratio=RECOMMENDATION_CAPACITY_RATIO,
    min_results=RECOMMENDATION_MIN_RESULTS,
):
    """
    Recibe productos ya ordenados por capacidad ascendente
    (todos con capacidad suficiente) y devuelve los que están
    cerca de la carga requerida.

    - Incluye todos los modelos con capacidad
      <= carga requerida * capacity_ratio.
    - Si quedan menos de min_results, completa con los
      siguientes modelos de menor capacidad disponibles.
    """

    products = list(products)
    max_capacity = float(required_load) * capacity_ratio

    close = [
        product
        for product in products
        if float(product.capacity_kg) <= max_capacity
    ]

    if len(close) < min_results:
        close = products[:max(min_results, len(close))]

    return close[:limit]
