import re


_KG_PATTERN = re.compile(
    r"(\d(?:[\d.,]*))\s*kg\b",
    re.IGNORECASE,
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