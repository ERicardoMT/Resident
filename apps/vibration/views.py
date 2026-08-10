from __future__ import annotations

import json

from django.http import (
    FileResponse,
    JsonResponse,
)
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import (
    require_POST,
)

from .analysis import analyze_samples
from .reports import build_measurement_pdf
from .serializers import (
    AnalyzeRequestSerializer,
)


def measure(request):
    """
    Pantalla de medición vibratoria en tiempo real.
    """

    return render(
        request,
        "vibration/measure.html",
    )


@require_POST
def measurement_pdf(request):
    """
    Recibe las muestras actuales, vuelve a analizarlas
    en el servidor y genera un reporte PDF.
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
                    "La solicitud debe ser "
                    "un objeto JSON."
                )
            },
            status=400,
        )

    selected_unit = payload.get(
        "measurement_unit",
        "acceleration",
    )

    if selected_unit not in {
        "acceleration",
        "velocity",
    }:
        return JsonResponse(
            {
                "detail": (
                    "La unidad de medición "
                    "no es válida."
                )
            },
            status=400,
        )

    serializer = (
        AnalyzeRequestSerializer(
            data={
                "samples": payload.get(
                    "samples",
                    [],
                )
            }
        )
    )

    if not serializer.is_valid():
        return JsonResponse(
            {
                "detail": (
                    "Las muestras recibidas "
                    "no son válidas."
                ),
                "errors": (
                    serializer.errors
                ),
            },
            status=400,
        )

    try:
        analysis = analyze_samples(
            serializer.validated_data[
                "samples"
            ]
        )
    except ValueError as exc:
        return JsonResponse(
            {
                "detail": str(exc)
            },
            status=400,
        )

    pdf_buffer = (
        build_measurement_pdf(
            analysis,
            selected_unit=selected_unit,
        )
    )

    timestamp = (
        timezone.localtime()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    filename = (
        "SMAV_INAHER_"
        "medicion_vibratoria_"
        f"{timestamp}.pdf"
    )

    return FileResponse(
        pdf_buffer,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )