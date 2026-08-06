from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "niveladores_campos_naranja.json"
)


MODEL_FIELD = "Modelo"

CAPACITY_FIELD = (
    "Capacidad de carga (título web)"
)

TYPE_FIELD = (
    "Tipo (según nombre/filtros web)"
)

METRIC_THREADS_FIELD = "Roscas métricas"

STANDARD_THREADS_FIELD = "Roscas estándar"

BASE_DIAMETER_FIELD = (
    "Diámetro de base (ficha web)"
)

SCREW_HEIGHT_FIELD = (
    "Altura de tornillo (ficha web)"
)

SCREW_MATERIAL_FIELD = (
    "Material de tornillo (ficha web)"
)

BASE_MATERIAL_FIELD = (
    "Material de base (ficha web)"
)


def normalize_text(value: Any) -> str:
    """
    Normaliza textos para facilitar las comparaciones.

    Ejemplo:
        Rótula / Antiderrapante
        rotula / antiderrapante
    """

    text = str(value or "").strip()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def normalize_thread(value: Any) -> str:
    """
    Normaliza una rosca para compararla.

    Ejemplos equivalentes:
        M12×1.75
        M12x1.75
        m12 x 1.75
    """

    thread = normalize_text(value)

    thread = thread.replace(
        "×",
        "x",
    )

    thread = thread.replace(
        " x ",
        "x",
    )

    thread = thread.replace(
        " ",
        "",
    )

    thread = thread.replace(
        "“",
        '"',
    )

    thread = thread.replace(
        "”",
        '"',
    )

    return thread


def parse_capacity_kg(value: Any) -> float | None:
    """
    Convierte la capacidad del catálogo a un número.

    Ejemplos:
        "150 Kg"       -> 150
        "1200 Kg"      -> 1200
        "1500-2000 Kg" -> 1500

    Para rangos se utiliza el valor inferior como
    capacidad conservadora.
    """

    text = str(value or "").strip()

    numbers = re.findall(
        r"\d+(?:[.,]\d+)?",
        text,
    )

    if not numbers:
        return None

    parsed_numbers = [
        float(
            number.replace(",", ".")
        )
        for number in numbers
    ]

    return min(parsed_numbers)


def split_threads(value: Any) -> list[str]:
    """
    Separa las roscas escritas en una celda.
    """

    text = str(value or "").strip()

    if not text or text == "—":
        return []

    return [
        thread.strip()
        for thread in text.split(",")
        if thread.strip()
        and thread.strip() != "—"
    ]


@lru_cache(maxsize=1)
def load_leveler_catalog() -> tuple[dict[str, Any], ...]:
    """
    Lee una sola vez el JSON generado desde Excel.

    La caché evita abrir el archivo en cada recomendación.
    """

    if not CATALOG_PATH.exists():
        raise FileNotFoundError(
            (
                "No se encontró el catálogo de niveladores:\n"
                f"{CATALOG_PATH}"
            )
        )

    try:
        catalog_data = json.loads(
            CATALOG_PATH.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            (
                "El catálogo de niveladores "
                "no contiene un JSON válido."
            )
        ) from exc

    sheets = catalog_data.get(
        "sheets",
        [],
    )

    records: list[dict[str, Any]] = []

    for sheet in sheets:
        sheet_name = str(
            sheet.get(
                "sheet",
                "",
            )
        ).strip()

        for raw_record in sheet.get(
            "records",
            [],
        ):
            if not isinstance(
                raw_record,
                dict,
            ):
                continue

            model = str(
                raw_record.get(
                    MODEL_FIELD,
                    "",
                )
                or ""
            ).strip()

            capacity_kg = parse_capacity_kg(
                raw_record.get(
                    CAPACITY_FIELD
                )
            )

            if not model:
                continue

            if capacity_kg is None:
                continue

            metric_threads = split_threads(
                raw_record.get(
                    METRIC_THREADS_FIELD
                )
            )

            standard_threads = split_threads(
                raw_record.get(
                    STANDARD_THREADS_FIELD
                )
            )

            record = {
                "model": model,
                "capacity_kg": capacity_kg,
                "capacity_label": str(
                    raw_record.get(
                        CAPACITY_FIELD,
                        "",
                    )
                    or ""
                ).strip(),
                "type": str(
                    raw_record.get(
                        TYPE_FIELD,
                        "",
                    )
                    or ""
                ).strip(),
                "metric_threads": metric_threads,
                "standard_threads": standard_threads,
                "base_diameter": str(
                    raw_record.get(
                        BASE_DIAMETER_FIELD,
                        "",
                    )
                    or ""
                ).strip(),
                "screw_height": str(
                    raw_record.get(
                        SCREW_HEIGHT_FIELD,
                        "",
                    )
                    or ""
                ).strip(),
                "screw_material": str(
                    raw_record.get(
                        SCREW_MATERIAL_FIELD,
                        "",
                    )
                    or ""
                ).strip(),
                "base_material": str(
                    raw_record.get(
                        BASE_MATERIAL_FIELD,
                        "",
                    )
                    or ""
                ).strip(),
                "excel_row": raw_record.get(
                    "_excel_row"
                ),
                "source_sheet": sheet_name,
            }

            records.append(record)

    if not records:
        raise ValueError(
            (
                "El catálogo no contiene "
                "niveladores válidos."
            )
        )

    return tuple(records)


def product_matches_application(
    product: dict[str, Any],
    application: str,
) -> bool:
    """
    Relaciona la aplicación con el campo Tipo.
    """

    product_type = normalize_text(
        product["type"]
    )

    normalized_application = normalize_text(
        application
    )

    if normalized_application == "furniture":
        return "mobiliario" in product_type

    if normalized_application == "industrial":
        return "mobiliario" not in product_type

    raise ValueError(
        "La aplicación debe ser furniture o industrial."
    )


def product_matches_special_mode(
    product: dict[str, Any],
    special_mode: str,
) -> bool:
    """
    Filtra por rótula o anclaje al piso.

    Línea normal no agrega un filtro especial.
    """

    product_type = normalize_text(
        product["type"]
    )

    normalized_mode = normalize_text(
        special_mode
    )

    if normalized_mode == "normal":
        return True

    if normalized_mode == "rotula":
        return "rotula" in product_type

    if normalized_mode == "anclaje":
        return "anclaje al piso" in product_type

    raise ValueError(
        (
            "El tipo de solicitud debe ser "
            "normal, rotula o anclaje."
        )
    )


def product_matches_sanitary(
    product: dict[str, Any],
    sanitary: bool,
) -> bool:
    """
    Para ambiente sanitario se solicita disponibilidad
    de acero inoxidable tanto en tornillo como en base.

    Esta es una regla inicial conservadora basada
    únicamente en los campos naranjas del catálogo.
    """

    if not sanitary:
        return True

    screw_material = normalize_text(
        product["screw_material"]
    )

    base_material = normalize_text(
        product["base_material"]
    )

    return (
        "inoxidable" in screw_material
        and "inoxidable" in base_material
    )


def product_matches_thread(
    product: dict[str, Any],
    requested_thread: str,
) -> bool:
    """
    Comprueba la rosca contra las listas métricas
    y estándar del producto.
    """

    normalized_requested = normalize_thread(
        requested_thread
    )

    if not normalized_requested:
        return True

    available_threads = (
        product["metric_threads"]
        + product["standard_threads"]
    )

    normalized_available = {
        normalize_thread(thread)
        for thread in available_threads
    }

    return (
        normalized_requested
        in normalized_available
    )


def serialize_product(
    product: dict[str, Any],
) -> dict[str, Any]:
    """
    Prepara un producto para enviarlo como JSON
    desde una vista de Django.
    """

    capacity = float(
        product["capacity_kg"]
    )

    if capacity.is_integer():
        serialized_capacity: int | float = int(
            capacity
        )
    else:
        serialized_capacity = capacity

    return {
        "model": product["model"],
        "capacity_kg": serialized_capacity,
        "capacity_label": product[
            "capacity_label"
        ],
        "type": product["type"],
        "metric_threads": product[
            "metric_threads"
        ],
        "standard_threads": product[
            "standard_threads"
        ],
        "base_diameter": product[
            "base_diameter"
        ],
        "screw_height": product[
            "screw_height"
        ],
        "screw_material": product[
            "screw_material"
        ],
        "base_material": product[
            "base_material"
        ],
    }


def sort_products(
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Ordena por la menor capacidad suficiente
    y posteriormente por modelo.
    """

    return sorted(
        products,
        key=lambda product: (
            product["capacity_kg"],
            normalize_text(
                product["model"]
            ),
        ),
    )


def recommend_levelers(
    application: str,
    weight: float,
    support_points: int,
    sanitary: bool,
    thread: str,
    special_mode: str,
) -> dict[str, Any]:
    """
    Busca una recomendación real en el catálogo.

    Orden de filtros:
        1. Aplicación.
        2. Tipo especial.
        3. Ambiente.
        4. Capacidad.
        5. Rosca.
    """

    try:
        normalized_weight = float(
            weight
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "El peso debe ser un número válido."
        ) from exc

    try:
        normalized_support_points = int(
            support_points
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            (
                "Los puntos de apoyo deben "
                "ser un número entero."
            )
        ) from exc

    if normalized_weight <= 0:
        raise ValueError(
            "El peso debe ser mayor que cero."
        )

    if normalized_support_points <= 0:
        raise ValueError(
            (
                "Los puntos de apoyo deben "
                "ser mayores que cero."
            )
        )

    load_per_point = (
        normalized_weight
        / normalized_support_points
    )

    catalog = list(
        load_leveler_catalog()
    )

    application_candidates = [
        product
        for product in catalog
        if product_matches_application(
            product,
            application,
        )
    ]

    type_candidates = [
        product
        for product in application_candidates
        if product_matches_special_mode(
            product,
            special_mode,
        )
    ]

    sanitary_candidates = [
        product
        for product in type_candidates
        if product_matches_sanitary(
            product,
            sanitary,
        )
    ]

    capacity_candidates = [
        product
        for product in sanitary_candidates
        if product["capacity_kg"]
        >= load_per_point
    ]

    capacity_candidates = sort_products(
        capacity_candidates
    )

    requested_thread = str(
        thread or ""
    ).strip()

    thread_candidates = [
        product
        for product in capacity_candidates
        if product_matches_thread(
            product,
            requested_thread,
        )
    ]

    thread_candidates = sort_products(
        thread_candidates
    )

    common_result = {
        "application": application,
        "weight_kg": round(
            normalized_weight,
            2,
        ),
        "support_points": (
            normalized_support_points
        ),
        "load_per_point_kg": round(
            load_per_point,
            2,
        ),
        "sanitary": bool(
            sanitary
        ),
        "requested_thread": (
            requested_thread
        ),
        "special_mode": special_mode,
        "catalog_count": len(
            catalog
        ),
    }

    if thread_candidates:
        recommended = thread_candidates[0]

        alternatives = [
            serialize_product(product)
            for product in thread_candidates[1:4]
        ]

        return {
            **common_result,
            "status": "recommended",
            "message": (
                "Se encontró una recomendación "
                "compatible con los filtros."
            ),
            "recommended": serialize_product(
                recommended
            ),
            "alternatives": alternatives,
            "matching_count": len(
                thread_candidates
            ),
        }

    if capacity_candidates:
        alternatives = [
            serialize_product(product)
            for product in capacity_candidates[:4]
        ]

        return {
            **common_result,
            "status": "thread_not_available",
            "message": (
                "Existen modelos compatibles con "
                "la carga y el tipo, pero no con "
                "la rosca solicitada."
            ),
            "recommended": None,
            "alternatives": alternatives,
            "matching_count": 0,
        }

    return {
        **common_result,
        "status": "no_match",
        "message": (
            "No se encontraron niveladores que "
            "cumplan todos los requisitos."
        ),
        "recommended": None,
        "alternatives": [],
        "matching_count": 0,
    }
def thread_sort_key(
    thread: str,
) -> tuple:
    """
    Genera una clave para ordenar roscas
    usando sus valores numéricos.
    """

    normalized = normalize_thread(
        thread
    )

    numbers = tuple(
        float(number)
        for number in re.findall(
            r"\d+(?:\.\d+)?",
            normalized,
        )
    )

    return (
        numbers,
        normalized,
    )


def get_available_threads() -> dict[str, list[str]]:
    """
    Devuelve las roscas únicas disponibles
    en los 84 registros del catálogo.
    """

    catalog = load_leveler_catalog()

    metric_threads = {
        thread
        for product in catalog
        for thread in product[
            "metric_threads"
        ]
    }

    standard_threads = {
        thread
        for product in catalog
        for thread in product[
            "standard_threads"
        ]
    }

    return {
        "metric": sorted(
            metric_threads,
            key=thread_sort_key,
        ),
        "standard": sorted(
            standard_threads,
            key=thread_sort_key,
        ),
    }