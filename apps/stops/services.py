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
    / "antivibratorios_campos_naranja.json"
)


MODEL_FIELD = "Modelo"
BASE_DIAMETER_FIELD = "Diámetro de base"
BASE_HEIGHT_FIELD = "Altura de base"
SCREW_DIAMETER_FIELD = "Diámetro de tornillo"
SCREW_HEIGHT_FIELD = "Altura de tornillo"
CAPACITY_FIELD = "Capacidad de carga"
ELASTOMER_MATERIAL_FIELD = "Material de elastómero"
SCREW_MATERIAL_FIELD = "Material de tornillo"
IMAGE_FIELD = "Imagen"
TECHNICAL_SHEET_FIELD = "Ficha técnica"


def normalize_text(value: Any) -> str:
    """
    Normaliza texto para comparaciones.
    """

    text = str(
        value or ""
    ).strip()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(
            character
        )
    )

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()



def extract_first_url(
    value: Any,
) -> str:
    """
    Extrae la primera URL encontrada.

    Algunas celdas contienen una URL seguida
    de una explicación entre paréntesis.
    """

    text = str(
        value or ""
    ).strip()

    match = re.search(
        r"https?://[^\s]+",
        text,
    )

    if not match:
        return ""

    return match.group(0).rstrip(
        ".,;)"
    )



def parse_capacity_kg(
    value: Any,
) -> float | None:
    """
    Convierte la capacidad del Excel
    a un número utilizable.

    Ejemplos:
        120 KG -> 120
        1500 KG -> 1500
        1500-2000 KG -> 1500

    Para un rango se toma el valor inferior
    de forma conservadora.
    """

    text = str(
        value or ""
    ).strip()

    numbers = re.findall(
        r"\d+(?:[.,]\d+)?",
        text,
    )

    if not numbers:
        return None

    values = [
        float(
            number.replace(
                ",",
                ".",
            )
        )
        for number in numbers
    ]

    return min(values)


@lru_cache(maxsize=1)
def load_antivibration_catalog(
) -> tuple[dict[str, Any], ...]:
    """
    Carga los registros provenientes únicamente
    de las columnas naranjas.
    """

    if not CATALOG_PATH.exists():
        raise FileNotFoundError(
            "No se encontró el catálogo "
            "de antivibratorios."
        )

    try:
        data = json.loads(
            CATALOG_PATH.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "El archivo de antivibratorios "
            "no contiene JSON válido."
        ) from exc

    records: list[
        dict[str, Any]
    ] = []

    for sheet in data.get(
        "sheets",
        [],
    ):
        sheet_name = str(
            sheet.get(
                "sheet",
                "",
            )
            or ""
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

            capacity_kg = (
                parse_capacity_kg(
                    raw_record.get(
                        CAPACITY_FIELD
                    )
                )
            )

            if not model:
                continue

            if capacity_kg is None:
                continue

            record = {
                "model": model,

                "base_diameter": str(
                    raw_record.get(
                        BASE_DIAMETER_FIELD,
                        "",
                    )
                    or ""
                ).strip(),

                "base_height": str(
                    raw_record.get(
                        BASE_HEIGHT_FIELD,
                        "",
                    )
                    or ""
                ).strip(),

                "screw_diameter": str(
                    raw_record.get(
                        SCREW_DIAMETER_FIELD,
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

                "capacity_kg": (
                    capacity_kg
                ),

                "capacity_label": str(
                    raw_record.get(
                        CAPACITY_FIELD,
                        "",
                    )
                    or ""
                ).strip(),

                "elastomer_material": str(
                    raw_record.get(
                        ELASTOMER_MATERIAL_FIELD,
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

                "image_url": extract_first_url(
                    raw_record.get(
                        IMAGE_FIELD,
                        "",
                    )
                ),

                "technical_sheet_url": extract_first_url(
                    raw_record.get(
                        TECHNICAL_SHEET_FIELD,
                        "",
                    )
                ),

                "excel_row": (
                    raw_record.get(
                        "_excel_row"
                    )
                ),

                "source_sheet": (
                    sheet_name
                ),
            }

            records.append(
                record
            )

    if not records:
        raise ValueError(
            "El catálogo no contiene "
            "antivibratorios válidos."
        )

    return tuple(records)


def matches_exact(
    product: dict[str, Any],
    field: str,
    requested_value: str,
) -> bool:
    """
    Un filtro vacío significa:
    Sin preferencia.
    """

    requested = normalize_text(
        requested_value
    )

    if not requested:
        return True

    available = normalize_text(
        product.get(
            field,
            "",
        )
    )

    return available == requested


def serialize_product(
    product: dict[str, Any],
) -> dict[str, Any]:

    capacity = float(
        product["capacity_kg"]
    )

    if capacity.is_integer():
        serialized_capacity = int(
            capacity
        )
    else:
        serialized_capacity = (
            capacity
        )

    return {
        "model": product["model"],

        "base_diameter": (
            product[
                "base_diameter"
            ]
        ),

        "base_height": (
            product[
                "base_height"
            ]
        ),

        "screw_diameter": (
            product[
                "screw_diameter"
            ]
        ),

        "screw_height": (
            product[
                "screw_height"
            ]
        ),

        "capacity_kg": (
            serialized_capacity
        ),

        "capacity_label": (
            product[
                "capacity_label"
            ]
        ),

        "elastomer_material": (
            product[
                "elastomer_material"
            ]
        ),

        "screw_material": (
            product[
                "screw_material"
            ]
        ),

        "image_url": (
            product.get(
                "image_url",
                "",
            )
        ),

        "technical_sheet_url": (
            product.get(
                "technical_sheet_url",
                "",
            )
        ),
    }


def sort_products(
    products: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:
    """
    Primero aparece la capacidad suficiente
    más cercana a la requerida.
    """

    return sorted(
        products,
        key=lambda product: (
            product[
                "capacity_kg"
            ],
            normalize_text(
                product[
                    "model"
                ]
            ),
        ),
    )


def get_selector_options(
) -> dict[str, list[str]]:
    """
    Genera automáticamente los valores
    disponibles desde las columnas naranjas.
    """

    catalog = (
        load_antivibration_catalog()
    )

    def unique_values(
        field: str,
    ) -> list[str]:

        return sorted(
            {
                str(
                    product.get(
                        field,
                        "",
                    )
                    or ""
                ).strip()
                for product in catalog
                if str(
                    product.get(
                        field,
                        "",
                    )
                    or ""
                ).strip()
            }
        )

    return {
        "base_diameters":
            unique_values(
                "base_diameter"
            ),

        "base_heights":
            unique_values(
                "base_height"
            ),

        "screw_diameters":
            unique_values(
                "screw_diameter"
            ),

        "screw_heights":
            unique_values(
                "screw_height"
            ),

        "elastomer_materials":
            unique_values(
                "elastomer_material"
            ),

        "screw_materials":
            unique_values(
                "screw_material"
            ),
    }


def recommend_antivibrators(
    weight: float,
    support_count: int,
    base_diameter: str = "",
    base_height: str = "",
    screw_diameter: str = "",
    screw_height: str = "",
    elastomer_material: str = "",
    screw_material: str = "",
) -> dict[str, Any]:
    """
    Recomendación basada exclusivamente
    en las ocho columnas naranjas.
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
            "El peso debe ser "
            "un número válido."
        ) from exc

    try:
        normalized_support_count = int(
            support_count
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "El número de apoyos debe "
            "ser un entero."
        ) from exc

    if normalized_weight <= 0:
        raise ValueError(
            "El peso debe ser "
            "mayor que cero."
        )

    if normalized_support_count <= 0:
        raise ValueError(
            "El número de apoyos debe "
            "ser mayor que cero."
        )

    required_load = (
        normalized_weight
        / normalized_support_count
    )

    catalog = list(
        load_antivibration_catalog()
    )

    candidates = [
        product
        for product in catalog
        if product[
            "capacity_kg"
        ] >= required_load
    ]

    candidates = sort_products(
        candidates
    )

    common_result = {
        "weight_kg": round(
            normalized_weight,
            2,
        ),

        "support_count": (
            normalized_support_count
        ),

        "required_load_kg": round(
            required_load,
            2,
        ),

        "catalog_count": len(
            catalog
        ),

        "requested": {
            "base_diameter":
                base_diameter,

            "base_height":
                base_height,

            "screw_diameter":
                screw_diameter,

            "screw_height":
                screw_height,

            "elastomer_material":
                elastomer_material,

            "screw_material":
                screw_material,
        },
    }

    if not candidates:
        return {
            **common_result,

            "status": "no_match",

            "failed_filter":
                "capacity",

            "message": (
                "No encontramos un "
                "antivibratorio con capacidad "
                "suficiente para la carga "
                "calculada."
            ),

            "recommended": None,
            "alternatives": [],
            "matching_count": 0,
        }

    filters = [
        (
            "base_diameter",
            "el diámetro de base",
            base_diameter,
        ),
        (
            "base_height",
            "la altura de base",
            base_height,
        ),
        (
            "screw_diameter",
            "el diámetro de tornillo",
            screw_diameter,
        ),
        (
            "screw_height",
            "la altura de tornillo",
            screw_height,
        ),
        (
            "elastomer_material",
            "el material de elastómero",
            elastomer_material,
        ),
        (
            "screw_material",
            "el material de tornillo",
            screw_material,
        ),
    ]

    for (
        field,
        label,
        requested_value,
    ) in filters:

        if not str(
            requested_value or ""
        ).strip():
            continue

        previous_candidates = (
            candidates
        )

        candidates = [
            product
            for product
            in candidates
            if matches_exact(
                product,
                field,
                requested_value,
            )
        ]

        candidates = sort_products(
            candidates
        )

        if not candidates:
            return {
                **common_result,

                "status":
                    "no_match",

                "failed_filter":
                    field,

                "message": (
                    "No encontramos un "
                    "antivibratorio que también "
                    f"cumpla {label}."
                ),

                "recommended":
                    None,

                "alternatives": [
                    serialize_product(
                        product
                    )
                    for product
                    in previous_candidates[
                        :4
                    ]
                ],

                "matching_count":
                    0,
            }

    recommended = (
        candidates[0]
    )

    alternatives = [
        serialize_product(
            product
        )
        for product
        in candidates[1:4]
    ]

    return {
        **common_result,

        "status": "recommended",

        "failed_filter": None,

        "message": (
            "Se encontró un "
            "antivibratorio compatible "
            "con las especificaciones."
        ),

        "recommended":
            serialize_product(
                recommended
            ),

        "alternatives":
            alternatives,

        "matching_count":
            len(candidates),
    }