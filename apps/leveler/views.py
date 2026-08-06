from __future__ import annotations

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services import (
    get_available_threads,
    recommend_levelers,
)


def select_leveler(request):
    """
    Muestra el selector y carga las roscas
    disponibles en el catálogo temporal.
    """

    available_threads = (
        get_available_threads()
    )

    return render(
        request,
        "leveler/select_leveler.html",
        {
            "metric_threads": (
                available_threads[
                    "metric"
                ]
            ),
            "standard_threads": (
                available_threads[
                    "standard"
                ]
            ),
        },
    )


@require_POST
def recommend_leveler(request):
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

    sanitary = payload.get(
        "sanitary",
        False,
    )

    if not isinstance(
        sanitary,
        bool,
    ):
        return JsonResponse(
            {
                "detail": (
                    "El campo sanitary debe "
                    "ser verdadero o falso."
                )
            },
            status=400,
        )

    try:
        result = recommend_levelers(
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
            sanitary=sanitary,
            thread=payload.get(
                "thread",
                "",
            ),
            special_mode=payload.get(
                "special_mode",
                "normal",
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
    Muestra el nivelador digital basado en
    los sensores de orientación del teléfono.
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