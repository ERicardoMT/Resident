from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from apps.core.models import (
    AntivibrationTechnicalData,
    CatalogCategory,
    CatalogSubcategory,
)

MAX_RECOMMENDATIONS = 8

ANTIVIBRATION_SUBCATEGORIES = [
    (
        CatalogSubcategory.COLGANTES,
        CatalogSubcategory.COLGANTES.label,
    ),
    (
        CatalogSubcategory.NIVELADORES_MAQUINARIA,
        CatalogSubcategory.NIVELADORES_MAQUINARIA.label,
    ),
    (
        CatalogSubcategory.PIES,
        CatalogSubcategory.PIES.label,
    ),
    (
        CatalogSubcategory.SOPORTES_PISO,
        CatalogSubcategory.SOPORTES_PISO.label,
    ),
    (
        CatalogSubcategory.TACONES,
        CatalogSubcategory.TACONES.label,
    ),
]

ANTIVIBRATION_SUBCATEGORY_LABELS = dict(
    ANTIVIBRATION_SUBCATEGORIES
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

        "subcategory":
            product.product.subcategory,

        "subcategory_label":
            (
                product.product.get_subcategory_display()
                if product.product.subcategory
                else ""
            ),    
    }


def get_selector_options(
) -> dict[str, Any]:
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
    
    available_subcategories = set(
        queryset
        .exclude(product__subcategory="")
        .values_list(
            "product__subcategory",
            flat=True,
        )
        .distinct()
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

        "subcategories": [
            {
                "value": value,
                "label": label,
            }
            for value, label
            in ANTIVIBRATION_SUBCATEGORIES
            if value in available_subcategories
        ],    
    }


def recommend_antivibrators(
    weight: float,
    support_count: int,
    subcategories: list[str] | None = None,
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

    if normalized_weight > Decimal("99999"):
        raise ValueError(
            "El peso máximo permitido no "
            "debe superar los 5 dígitos."
        )

    if (
        normalized_weight
        != normalized_weight.to_integral_value()
    ):
        raise ValueError(
            "El peso debe ser un "
            "número entero."
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

    if subcategories is None:
        subcategories = []

    if not isinstance(
        subcategories,
        list,
    ):
        raise ValueError(
            "Las categorías seleccionadas "
            "no tienen un formato válido."
        )

    selected_subcategories = list(
        dict.fromkeys(
            clean_value(value)
            for value in subcategories
            if clean_value(value)
        )
    )

    invalid_subcategories = [
        value
        for value in selected_subcategories
        if value
        not in ANTIVIBRATION_SUBCATEGORY_LABELS
    ]

    if invalid_subcategories:
        raise ValueError(
            "Una o más categorías de "
            "antivibratorio no son válidas."
        )

    selected_subcategory_labels = [
        ANTIVIBRATION_SUBCATEGORY_LABELS[
            value
        ]
        for value in selected_subcategories
    ]

    catalog_queryset = (
        get_catalog_queryset()
    )

    catalog_count = (
        catalog_queryset.count()
    )

    filtered_catalog = catalog_queryset

    if selected_subcategories:
        filtered_catalog = (
            filtered_catalog.filter(
                product__subcategory__in=(
                    selected_subcategories
                )
            )
        )

    subcategory_count = (
        filtered_catalog.count()    
    )

    candidates = (
        filtered_catalog
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

        "requested_subcategories":
            selected_subcategories,

        "requested_subcategory_labels":
            selected_subcategory_labels,

        "requested_subcategory_label":
            " · ".join(
                selected_subcategory_labels
            ),

        "subcategory_count":
            subcategory_count,
      
    }

    if (
    selected_subcategories
    and subcategory_count == 0
    ):
        return {
            **common_result,
            "status": "no_match",
            "failed_filter": "subcategory",
            "message": (
                "No encontramos antivibratorios "
                "disponibles en las categorías seleccionadas."
            ),
            "recommended": None,
            "alternatives": [],
            "matching_count": 0,
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
                    :MAX_RECOMMENDATIONS
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
        candidates[
            :MAX_RECOMMENDATIONS
        ]
    )

    recommended = (
        products[0]
    )

    alternatives = [
        serialize_product(
            product
        )
        for product in products[1:MAX_RECOMMENDATIONS]
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