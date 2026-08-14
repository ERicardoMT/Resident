from __future__ import annotations

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services import (
    get_selector_options,
    recommend_levelers_v2,
)


def select_leveler(request):
    """
    Muestra el selector usando las opciones
    obtenidas del catálogo actualizado.
    """

    selector_options = (
        get_selector_options()
    )

    return render(
        request,
        "leveler/select_leveler.html",
        {
            "selector_options": (
                selector_options
            ),
        },
    )


@require_POST
def recommend_leveler(request):
    """
    Recibe los datos del nuevo selector.
    """

    try:
        payload = json.loads(
            request.body.decode("utf-8")
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

    if not isinstance(payload, dict):
        return JsonResponse(
            {
                "detail": (
                    "El cuerpo de la solicitud "
                    "debe ser un objeto JSON."
                )
            },
            status=400,
        )

    features = payload.get(
        "features",
        [],
    )

    if not isinstance(features, list):
        return JsonResponse(
            {
                "detail": (
                    "Las características deben "
                    "enviarse como una lista."
                )
            },
            status=400,
        )

    features = [
        str(feature).strip()
        for feature in features
        if str(feature).strip()
    ]

    try:
        result = recommend_levelers_v2(
            application=payload.get(
                "application",
                "",
            ),
            weight=payload.get(
                "weight"
            ),
            support_points=payload.get(
                "support_points"
            ),
            features=features,
            thread=payload.get(
                "thread",
                "",
            ),
            base_diameter=payload.get(
                "base_diameter",
                "",
            ),
            screw_height=payload.get(
                "screw_height",
                "",
            ),
            screw_material=payload.get(
                "screw_material",
                "",
            ),
            base_material=payload.get(
                "base_material",
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


def leveler(request):
    """
    Nivel digital con sensores.
    """

    response = render(
        request,
        "leveler/leveler.html",
    )

    response.headers[
        "Permissions-Policy"
    ] = (
        "accelerometer=(self), "
        "gyroscope=(self)"
    )

    return response