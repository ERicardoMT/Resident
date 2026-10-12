from __future__ import annotations

import json
import uuid
from io import BytesIO

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
from .models import VibrationMeasurement
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
    Genera el PDF de una medición vibratoria.

    Además:
    - genera el folio en el servidor;
    - guarda los resultados en PostgreSQL;
    - guarda el PDF completo en PostgreSQL;
    - evita duplicar una misma medición.
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


        # =====================================================
    # Identificador único de esta medición
    # =====================================================

    measurement_token_value = (
        payload.get(
            "measurement_token"
        )
        or ""
    )


    if measurement_token_value:

        try:
            measurement_token = uuid.UUID(
                str(
                    measurement_token_value
                )
            )

        except (
            ValueError,
            TypeError,
            AttributeError,
        ):
            return JsonResponse(
                {
                    "detail": (
                        "El identificador de la "
                        "medición no es válido."
                    )
                },
                status=400,
            )

    else:

        measurement_token = (
            uuid.uuid4()
        )


    # =====================================================
    # Buscar si esta medición ya fue guardada
    # =====================================================

    existing_measurement = (
        VibrationMeasurement.objects
        .filter(
            measurement_token=(
                measurement_token
            )
        )
        .first()
    )


    # =====================================================
    # Si ya existe, devolver el mismo PDF
    # sin crear otro registro.
    # =====================================================

    if existing_measurement:

        response = FileResponse(
            BytesIO(
                bytes(
                    existing_measurement
                    .pdf_data
                )
            ),
            as_attachment=True,
            filename=(
                existing_measurement
                .pdf_filename
            ),
            content_type=(
                "application/pdf"
            ),
        )

        response[
            "X-SMAV-Folio"
        ] = (
            existing_measurement.folio
        )

        return response


    # =====================================================
    # Validar muestras
    # =====================================================


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


    # =====================================================
    # Analizar medición
    # =====================================================

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


    # =====================================================
    # Generar folio en el servidor
    # =====================================================

    date_text = (
        timezone.localdate()
        .strftime(
            "%Y%m%d"
        )
    )


    folio = (
        "SMAV-"
        + date_text
        + "-"
        + measurement_token.hex[
            :10
        ].upper()
    )


    # =====================================================
    # Generar PDF usando ESE MISMO folio
    # =====================================================

    pdf_buffer = (
        build_measurement_pdf(
            analysis,
            selected_unit=(
                selected_unit
            ),
            folio=folio,
        )
    )


    pdf_bytes = (
        pdf_buffer.getvalue()
    )


    filename = (
        "SMAV_INAHER_"
        "medicion_vibratoria_"
        f"{folio}.pdf"
    )


    # =====================================================
    # Guardar medición completa en PostgreSQL
    # =====================================================

    measurement = (
        VibrationMeasurement.objects.create(
            measurement_token=(
                measurement_token
            ),

            folio=folio,

            measurement_unit=(
                selected_unit
            ),

            dominant_hz=(
                analysis.get(
                    "dominant_hz",
                    0.0,
                )
            ),

            rpm=(
                analysis.get(
                    "rpm",
                    0.0,
                )
            ),

            sample_rate_hz=(
                analysis.get(
                    "sample_rate_hz",
                    0.0,
                )
            ),

            sample_count=(
                analysis.get(
                    "sample_count",
                    0,
                )
            ),

            duration_s=(
                analysis.get(
                    "duration_s",
                    0.0,
                )
            ),

            rms_ms2=(
                analysis.get(
                    "rms_ms2",
                    0.0,
                )
            ),

            rms_g=(
                analysis.get(
                    "rms_g",
                    0.0,
                )
            ),

            peak_ms2=(
                analysis.get(
                    "peak_ms2",
                    0.0,
                )
            ),

            peak_g=(
                analysis.get(
                    "peak_g",
                    0.0,
                )
            ),

            velocity_rms_mms=(
                analysis.get(
                    "velocity_rms_mms",
                    0.0,
                )
            ),

            velocity_peak_mms=(
                analysis.get(
                    "velocity_peak_mms",
                    0.0,
                )
            ),

            analysis_data=analysis,

            pdf_filename=filename,

            pdf_data=pdf_bytes,
        )
    )


    response = FileResponse(
    BytesIO(
        bytes(
            measurement.pdf_data
        )
    ),
    as_attachment=True,
    filename=(
        measurement.pdf_filename
    ),
    content_type=(
        "application/pdf"
    ),
)

    response[
        "X-SMAV-Folio"
    ] = (
        measurement.folio
    )   

    return response