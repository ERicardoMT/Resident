from __future__ import annotations

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services import (
    get_selector_options,
    recommend_antivibrators,
)


def stops(request):
    """
    Muestra el selector y carga las opciones
    disponibles desde el catálogo.
    """

    selector_options = (
        get_selector_options()
    )

    return render(
        request,
        "stops/stops.html",
        {
            "selector_options": (
                selector_options
            ),
        },
    )


@require_POST
def recommend_antivibrator(request):
    """
    Recibe los datos del formulario y devuelve
    una recomendación calculada desde el catálogo.
    """

    try:
        payload = json.loads(
            request.body.decode(
                "utf-8"
            )
            or "{}"
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return JsonResponse(
            {
                "detail": (
                    "La solicitud no contiene "
                    "un JSON válido."
                )
            },
            status=400,
        )

    if not isinstance(
        payload,
        dict,
    ):
        return JsonResponse(
            {
                "detail": (
                    "El cuerpo de la solicitud "
                    "debe ser un objeto JSON."
                )
            },
            status=400,
        )

    try:
        result = recommend_antivibrators(
            weight=payload.get(
                "weight"
            ),
            support_count=payload.get(
                "support_count"
            ),
            base_diameter=payload.get(
                "base_diameter",
                "",
            ),
            base_height=payload.get(
                "base_height",
                "",
            ),
            screw_diameter=payload.get(
                "screw_diameter",
                "",
            ),
            screw_height=payload.get(
                "screw_height",
                "",
            ),
            elastomer_material=payload.get(
                "elastomer_material",
                "",
            ),
            screw_material=payload.get(
                "screw_material",
                "",
            ),
        )

    except (
        FileNotFoundError,
        ValueError,
    ) as exc:
        return JsonResponse(
            {
                "detail": str(exc)
            },
            status=400,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    return JsonResponse(
        result,
        status=200,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )