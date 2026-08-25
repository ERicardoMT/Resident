from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from apps.core.models import (
    AntivibrationTechnicalData,
    CatalogCategory,
)


def get_catalog_queryset():
    """
    Devuelve únicamente antivibratorios activos
    que tienen una capacidad válida.
    """

    return (
        AntivibrationTechnicalData.objects
        .select_related("product")
        .filter(
            product__category=(
                CatalogCategory.ANTIVIBRATORIOS
            ),
            product__is_active=True,
            capacity_kg__isnull=False,
        )
    )


def clean_value(
    value: Any,
) -> str:
    return str(
        value or ""
    ).strip()


def serialize_capacity(
    value,
):
    """
    Convierte Decimal a un valor apto
    para enviar como JSON.
    """

    if value is None:
        return None

    number = float(value)

    if number.is_integer():
        return int(number)

    return number


def serialize_product(
    product: AntivibrationTechnicalData,
) -> dict[str, Any]:
    """
    Convierte un registro de PostgreSQL
    al formato que ya utiliza el frontend.
    """

    return {
        "id": product.product_id,

        "model":
            product.model_code,

        "base_diameter":
            product.base_diameter,

        "base_height":
            product.base_height,

        "screw_diameter":
            product.screw_diameter,

        "screw_height":
            product.screw_height,

        "capacity_kg":
            serialize_capacity(
                product.capacity_kg
            ),

        "capacity_label":
            product.capacity_label,

        "elastomer_material":
            product.elastomer_material,

        "screw_material":
            product.screw_material,

        "image_url":
            product.product.catalog_image_url,

        "technical_sheet_url":
            product.product.catalog_technical_sheet_url,
    }


def get_selector_options(
) -> dict[str, list[str]]:
    """
    Construye las opciones del formulario
    directamente desde PostgreSQL.
    """

    queryset = get_catalog_queryset()

    def unique_values(
        field_name: str,
    ) -> list[str]:

        values = (
            queryset
            .exclude(
                **{
                    field_name: "",
                }
            )
            .values_list(
                field_name,
                flat=True,
            )
            .distinct()
        )

        return sorted(
            {
                clean_value(value)
                for value in values
                if clean_value(value)
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
    Busca antivibratorios directamente
    en PostgreSQL.

    Orden:
    1. Peso / número de apoyos.
    2. Capacidad suficiente.
    3. Filtros técnicos opcionales.
    4. Menor capacidad suficiente.
    """

    try:
        normalized_weight = Decimal(
            str(weight)
        )
    except (
        InvalidOperation,
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
            "ser un entero válido."
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
        / Decimal(
            normalized_support_count
        )
    )

    catalog_queryset = (
        get_catalog_queryset()
    )

    catalog_count = (
        catalog_queryset.count()
    )

    candidates = (
        catalog_queryset
        .filter(
            capacity_kg__gt=(
                required_load
            )
        )
        .order_by(
            "capacity_kg",
            "model_code",
        )
    )

    common_result = {
        "weight_kg":
            float(
                normalized_weight
            ),

        "support_count":
            normalized_support_count,

        "required_load_kg":
            round(
                float(
                    required_load
                ),
                2,
            ),

        "catalog_count":
            catalog_count,

        "requested": {
            "base_diameter":
                clean_value(
                    base_diameter
                ),

            "base_height":
                clean_value(
                    base_height
                ),

            "screw_diameter":
                clean_value(
                    screw_diameter
                ),

            "screw_height":
                clean_value(
                    screw_height
                ),

            "elastomer_material":
                clean_value(
                    elastomer_material
                ),

            "screw_material":
                clean_value(
                    screw_material
                ),
        },
    }

    if not candidates.exists():
        return {
            **common_result,

            "status":
                "no_match",

            "failed_filter":
                "capacity",

            "message": (
                "No encontramos un "
                "antivibratorio con capacidad "
                "suficiente para la carga "
                "calculada."
            ),

            "recommended":
                None,

            "alternatives":
                [],

            "matching_count":
                0,
        }

    filters = [
        (
            "base_diameter",
            clean_value(
                base_diameter
            ),
            "el diámetro de base",
        ),
        (
            "base_height",
            clean_value(
                base_height
            ),
            "la altura de base",
        ),
        (
            "screw_diameter",
            clean_value(
                screw_diameter
            ),
            "el diámetro de tornillo",
        ),
        (
            "screw_height",
            clean_value(
                screw_height
            ),
            "la altura de tornillo",
        ),
        (
            "elastomer_material",
            clean_value(
                elastomer_material
            ),
            "el material de elastómero",
        ),
        (
            "screw_material",
            clean_value(
                screw_material
            ),
            "el material de tornillo",
        ),
    ]

    for (
        field_name,
        requested_value,
        label,
    ) in filters:

        if not requested_value:
            continue

        previous_candidates = (
            candidates
        )

        candidates = (
            candidates
            .filter(
                **{
                    field_name:
                        requested_value,
                }
            )
            .order_by(
                "capacity_kg",
                "model_code",
            )
        )

        if not candidates.exists():

            alternatives = [
                serialize_product(
                    product
                )
                for product
                in previous_candidates[
                    :4
                ]
            ]

            return {
                **common_result,

                "status":
                    "no_match",

                "failed_filter":
                    field_name,

                "message": (
                    "No encontramos un "
                    "antivibratorio que también "
                    f"cumpla {label}."
                ),

                "recommended":
                    None,

                "alternatives":
                    alternatives,

                "matching_count":
                    0,
            }

    matching_count = (
        candidates.count()
    )

    products = list(
        candidates[:4]
    )

    recommended = (
        products[0]
    )

    alternatives = [
        serialize_product(
            product
        )
        for product in products[1:]
    ]

    return {
        **common_result,

        "status":
            "recommended",

        "failed_filter":
            None,

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
            matching_count,
    }