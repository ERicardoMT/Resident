from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.core.models import (
    CatalogCategory,
    LevelerTechnicalData,
)


def normalize_text(
    value: Any,
) -> str:
    """
    Normaliza texto para realizar
    comparaciones consistentes.
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


def normalize_thread(
    value: Any,
) -> str:
    """
    Normaliza una rosca.

    Ejemplos equivalentes:

    M12×1.75
    M12x1.75
    m12 x 1.75
    """

    thread = normalize_text(
        value
    )

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


def split_threads(
    value: Any,
) -> list[str]:
    """
    Convierte una celda de roscas
    en una lista.
    """

    text = str(
        value or ""
    ).strip()

    if (
        not text
        or text == "—"
    ):
        return []

    return [
        thread.strip()
        for thread in re.split(
            r"[,;\n]+",
            text,
        )
        if thread.strip()
        and thread.strip() != "—"
    ]


def thread_sort_key(
    thread: str,
) -> tuple:
    """
    Ordena las roscas por sus
    componentes numéricos.
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


def get_catalog_queryset():
    """
    Obtiene los niveladores activos
    directamente desde PostgreSQL.
    """

    return (
        LevelerTechnicalData.objects
        .select_related(
            "product"
        )
        .filter(
            product__is_active=True,
            product__category__in=[
                CatalogCategory
                .PATAS_NIVELADORAS,

                CatalogCategory
                .MOBILIARIO,
            ],
            capacity_kg__isnull=False,
        )
    )


def application_category(
    application: str,
):
    """
    Relaciona el selector de aplicación
    con la categoría del catálogo.
    """

    normalized = normalize_text(
        application
    )

    if normalized == "furniture":
        return (
            CatalogCategory.MOBILIARIO
        )

    if normalized == "industrial":
        return (
            CatalogCategory
            .PATAS_NIVELADORAS
        )

    raise ValueError(
        "La aplicación debe ser "
        "furniture o industrial."
    )


def product_matches_features(
    product: LevelerTechnicalData,
    requested_features: list[str],
) -> bool:
    """
    Comprueba que el tipo del producto
    tenga todas las características
    seleccionadas.
    """

    if not requested_features:
        return True

    product_features = {
        normalize_text(
            feature
        )
        for feature in str(
            product.type_label or ""
        ).split("/")
        if feature.strip()
    }

    normalized_requested = {
        normalize_text(
            feature
        )
        for feature
        in requested_features
        if str(feature).strip()
    }

    return (
        normalized_requested
        .issubset(
            product_features
        )
    )


def product_matches_thread(
    product: LevelerTechnicalData,
    requested_thread: str,
) -> bool:
    """
    Busca la rosca tanto en el campo
    métrico como estándar.
    """

    normalized_requested = (
        normalize_thread(
            requested_thread
        )
    )

    if not normalized_requested:
        return True

    available_threads = (
        split_threads(
            product.metric_threads
        )
        +
        split_threads(
            product.standard_threads
        )
    )

    normalized_available = {
        normalize_thread(
            thread
        )
        for thread
        in available_threads
    }

    return (
        normalized_requested
        in normalized_available
    )


def product_matches_exact_field(
    product: LevelerTechnicalData,
    field_name: str,
    requested_value: str,
) -> bool:
    """
    Compara exactamente un campo técnico.

    Una solicitud vacía no agrega filtro.
    """

    requested = normalize_text(
        requested_value
    )

    if not requested:
        return True

    product_value = normalize_text(
        getattr(
            product,
            field_name,
            "",
        )
    )

    return (
        product_value
        == requested
    )


def serialize_capacity(
    value,
):
    """
    Convierte Decimal a int o float
    para poder devolverlo como JSON.
    """

    if value is None:
        return None

    number = float(
        value
    )

    if number.is_integer():
        return int(
            number
        )

    return number


def get_image_url(
    product: LevelerTechnicalData,
) -> str:
    """
    Usa primero una imagen cargada
    directamente en CatalogItem.

    Como respaldo busca una URL
    almacenada en la fila original
    importada desde Excel.
    """

    catalog_product = (
        product.product
    )

    if (
        catalog_product.image
        and catalog_product.image.name
    ):
        try:
            return (
                catalog_product.image.url
            )
        except ValueError:
            pass

    raw_data = (
        product.raw_data
        if isinstance(
            product.raw_data,
            dict,
        )
        else {}
    )

    for field_name in (
        "Imagen principal",
        "Imagen",
        "URL de imagen",
    ):
        value = str(
            raw_data.get(
                field_name,
                "",
            )
            or ""
        ).strip()

        if value:
            return value

    return ""


def serialize_product(
    product: LevelerTechnicalData,
) -> dict[str, Any]:
    """
    Prepara un nivelador para enviarlo
    al frontend como JSON.
    """

    return {
        "id":
            product.product_id,

        "model":
            product.model_code,

        "capacity_kg":
            serialize_capacity(
                product.capacity_kg
            ),

        "capacity_label":
            product.capacity_label,

        "type":
            product.type_label,

        "metric_threads":
            split_threads(
                product.metric_threads
            ),

        "standard_threads":
            split_threads(
                product.standard_threads
            ),

        "base_diameter":
            product.base_diameter,

        "screw_height":
            product.screw_height,

        "screw_material":
            product.screw_material,

        "base_material":
            product.base_material,

        "product_url":
            product.product_url,

        "image_url":
            get_image_url(
                product
            ),
    }


def sort_products(
    products: list[
        LevelerTechnicalData
    ],
) -> list[
    LevelerTechnicalData
]:
    """
    Ordena por la menor capacidad
    suficiente y después por modelo.
    """

    return sorted(
        products,
        key=lambda product: (
            float(
                product.capacity_kg
            ),
            normalize_text(
                product.model_code
            ),
        ),
    )


def get_available_threads(
) -> dict[str, list[str]]:
    """
    Obtiene todas las roscas disponibles
    directamente desde PostgreSQL.
    """

    catalog = (
        get_catalog_queryset()
    )

    metric_threads: set[str] = set()

    standard_threads: set[str] = set()

    for product in catalog:

        metric_threads.update(
            split_threads(
                product.metric_threads
            )
        )

        standard_threads.update(
            split_threads(
                product.standard_threads
            )
        )

    return {
        "metric":
            sorted(
                metric_threads,
                key=thread_sort_key,
            ),

        "standard":
            sorted(
                standard_threads,
                key=thread_sort_key,
            ),
    }


def get_selector_options(
) -> dict[str, list[str]]:
    """
    Genera todas las opciones del
    selector desde PostgreSQL.
    """

    catalog = (
        get_catalog_queryset()
    )

    type_features: set[str] = set()

    diameters: set[str] = set()

    heights: set[str] = set()

    screw_materials: set[str] = set()

    base_materials: set[str] = set()

    for product in catalog:

        product_type = str(
            product.type_label
            or ""
        ).strip()

        if product_type:

            for feature in (
                product_type.split("/")
            ):

                feature = (
                    feature.strip()
                )

                if (
                    feature
                    and normalize_text(
                        feature
                    )
                    != "mobiliario"
                ):
                    type_features.add(
                        feature
                    )

        base_diameter = str(
            product.base_diameter
            or ""
        ).strip()

        if base_diameter:
            diameters.add(
                base_diameter
            )

        screw_height = str(
            product.screw_height
            or ""
        ).strip()

        if screw_height:
            heights.add(
                screw_height
            )

        screw_material = str(
            product.screw_material
            or ""
        ).strip()

        if screw_material:
            screw_materials.add(
                screw_material
            )

        base_material = str(
            product.base_material
            or ""
        ).strip()

        if base_material:
            base_materials.add(
                base_material
            )

    threads = (
        get_available_threads()
    )

    return {
        "type_features":
            sorted(
                type_features
            ),

        "metric_threads":
            threads["metric"],

        "standard_threads":
            threads["standard"],

        "diameters":
            sorted(
                diameters
            ),

        "heights":
            sorted(
                heights
            ),

        "screw_materials":
            sorted(
                screw_materials
            ),

        "base_materials":
            sorted(
                base_materials
            ),
    }


def recommend_levelers_v2(
    application: str,
    weight: float,
    support_points: int,
    features: list[str] | None = None,
    thread: str = "",
    base_diameter: str = "",
    screw_height: str = "",
    screw_material: str = "",
    base_material: str = "",
) -> dict[str, Any]:
    """
    Recomienda niveladores utilizando
    exclusivamente PostgreSQL.

    Orden de evaluación:

    1. Aplicación.
    2. Capacidad.
    3. Características.
    4. Rosca.
    5. Diámetro de base.
    6. Altura de tornillo.
    7. Material de tornillo.
    8. Material de base.
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
        normalized_support_points = int(
            support_points
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Los puntos de apoyo deben "
            "ser un número entero."
        ) from exc

    if normalized_weight <= 0:
        raise ValueError(
            "El peso debe ser "
            "mayor que cero."
        )

    if normalized_support_points <= 0:
        raise ValueError(
            "Los puntos de apoyo deben "
            "ser mayores que cero."
        )

    category = (
        application_category(
            application
        )
    )

    requested_features = [
        str(feature).strip()
        for feature
        in (features or [])
        if str(feature).strip()
    ]

    load_per_point = (
        normalized_weight
        /
        Decimal(
            normalized_support_points
        )
    )

    catalog = (
        get_catalog_queryset()
    )

    catalog_count = (
        catalog.count()
    )

    application_queryset = (
        catalog.filter(
            product__category=category
        )
    )

    application_count = (
        application_queryset.count()
    )

    common_result = {
        "application":
            application,

        "weight_kg":
            round(
                float(
                    normalized_weight
                ),
                2,
            ),

        "support_points":
            normalized_support_points,

        "load_per_point_kg":
            round(
                float(
                    load_per_point
                ),
                2,
            ),

        "requested_features":
            requested_features,

        "requested_thread":
            str(
                thread or ""
            ).strip(),

        "requested_base_diameter":
            str(
                base_diameter or ""
            ).strip(),

        "requested_screw_height":
            str(
                screw_height or ""
            ).strip(),

        "requested_screw_material":
            str(
                screw_material or ""
            ).strip(),

        "requested_base_material":
            str(
                base_material or ""
            ).strip(),

        "catalog_count":
            catalog_count,

        "application_count":
            application_count,
    }

    if not application_count:

        return {
            **common_result,

            "status":
                "no_match",

            "failed_filter":
                "application",

            "message": (
                "No existen modelos para "
                "la aplicación seleccionada."
            ),

            "recommended":
                None,

            "alternatives":
                [],

            "matching_count":
                0,
        }

    capacity_queryset = (
        application_queryset
        .filter(
            capacity_kg__gte=(
                load_per_point
            )
        )
        .order_by(
            "capacity_kg",
            "model_code",
        )
    )

    candidates = list(
        capacity_queryset
    )

    if not candidates:

        return {
            **common_result,

            "status":
                "no_match",

            "failed_filter":
                "capacity",

            "message": (
                "No existen modelos con "
                "capacidad suficiente para "
                "la carga calculada."
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
            "features",
            "las características "
            "seleccionadas",
            lambda product: (
                product_matches_features(
                    product,
                    requested_features,
                )
            ),
            bool(
                requested_features
            ),
        ),

        (
            "thread",
            "la rosca seleccionada",
            lambda product: (
                product_matches_thread(
                    product,
                    thread,
                )
            ),
            bool(
                str(
                    thread or ""
                ).strip()
            ),
        ),

        (
            "base_diameter",
            "el diámetro de base",
            lambda product: (
                product_matches_exact_field(
                    product,
                    "base_diameter",
                    base_diameter,
                )
            ),
            bool(
                str(
                    base_diameter or ""
                ).strip()
            ),
        ),

        (
            "screw_height",
            "la altura de tornillo",
            lambda product: (
                product_matches_exact_field(
                    product,
                    "screw_height",
                    screw_height,
                )
            ),
            bool(
                str(
                    screw_height or ""
                ).strip()
            ),
        ),

        (
            "screw_material",
            "el material del tornillo",
            lambda product: (
                product_matches_exact_field(
                    product,
                    "screw_material",
                    screw_material,
                )
            ),
            bool(
                str(
                    screw_material or ""
                ).strip()
            ),
        ),

        (
            "base_material",
            "el material de base",
            lambda product: (
                product_matches_exact_field(
                    product,
                    "base_material",
                    base_material,
                )
            ),
            bool(
                str(
                    base_material or ""
                ).strip()
            ),
        ),
    ]

    for (
        filter_name,
        filter_label,
        filter_function,
        is_active,
    ) in filters:

        if not is_active:
            continue

        previous_candidates = (
            candidates
        )

        candidates = [
            product
            for product
            in candidates
            if filter_function(
                product
            )
        ]

        candidates = (
            sort_products(
                candidates
            )
        )

        if not candidates:

            return {
                **common_result,

                "status":
                    "no_match",

                "failed_filter":
                    filter_name,

                "message": (
                    "No encontramos un "
                    "modelo que también "
                    f"cumpla {filter_label}."
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

    candidates = (
        sort_products(
            candidates
        )
    )

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

        "status":
            "recommended",

        "failed_filter":
            None,

        "message": (
            "Se encontró una "
            "recomendación compatible "
            "con las especificaciones."
        ),

        "recommended":
            serialize_product(
                recommended
            ),

        "alternatives":
            alternatives,

        "matching_count":
            len(
                candidates
            ),
    }