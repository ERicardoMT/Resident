from __future__ import annotations

import json
import os
import uuid
from io import BytesIO

from django.contrib.staticfiles import finders
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import (
    FileResponse,
    JsonResponse,
)
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.shortcuts import (
    get_object_or_404,
    render,
)
from django.utils import timezone
from django.views.decorators.http import (
    require_POST,
)

from apps.core.ratelimit import client_ip, hit, is_limited

from .analysis import analyze_samples
from .reports import build_measurement_pdf
from .models import VibrationMeasurement
from .serializers import (
    AnalyzeRequestSerializer,
)


# Mediciones por página en el panel
MEASUREMENTS_PAGE_SIZE = 25

# Límite de PDF por IP: 30 cada 10 minutos
PDF_RATE_SCOPE = "measurement-pdf"
PDF_RATE_LIMIT = 30
PDF_RATE_WINDOW_S = 10 * 60


def measure(request):
    """
    Pantalla de medición vibratoria en tiempo real.
    """

    # Versión del JS por fecha de modificación: obliga a cualquier
    # navegador (Safari incluido) a bajar la versión nueva y no la de caché.
    js_path = finders.find(
        "js/vibration.js"
    )

    vibration_js_version = (
        int(os.path.getmtime(js_path))
        if js_path
        else 0
    )

    return render(
        request,
        "vibration/measure.html",
        {
            "vibration_js_version": (
                vibration_js_version
            ),
        },
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

    # Cada PDF se guarda en la base: se limita para que un script
    # no pueda llenarla (un cliente real genera unos cuantos)
    ip = client_ip(request)

    if is_limited(PDF_RATE_SCOPE, ip, PDF_RATE_LIMIT):
        return JsonResponse(
            {
                "detail": (
                    "Generaste muchos PDF seguidos. "
                    "Espera unos minutos e intenta de nuevo."
                )
            },
            status=429,
        )

    hit(PDF_RATE_SCOPE, ip, PDF_RATE_WINDOW_S)

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
                ),
                # Mismos datos que /api/analyze/ para que
                # pantalla y PDF den el mismo número (decisión 10)
                "rpm_placa": payload.get(
                    "rpm_placa"
                ),
                "gravity_included": payload.get(
                    "gravity_included",
                    False,
                ),
                "user_agent": payload.get(
                    "user_agent",
                    "",
                ),
                "audio_pcm16": payload.get(
                    "audio_pcm16"
                ),
                "audio_sample_rate": payload.get(
                    "audio_sample_rate"
                ),
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
            samples=serializer.validated_data[
                "samples"
            ],
            rpm_placa=serializer.validated_data.get(
                "rpm_placa"
            ),
            gravity_included=serializer.validated_data.get(
                "gravity_included",
                False,
            ),
            user_agent=serializer.validated_data.get(
                "user_agent",
                "",
            ),
            audio_pcm16=serializer.validated_data.get(
                "audio_pcm16"
            ),
            audio_sample_rate=serializer.validated_data.get(
                "audio_sample_rate"
            ),
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

    # Dos envíos casi simultáneos con el mismo identificador (doble toque):
    # el segundo choca con el índice único y recibe el PDF ya guardado
    try:
        with transaction.atomic():
            measurement = (
                VibrationMeasurement.objects.create(
                    measurement_token=(
                        measurement_token
                    ),

                    folio=folio,

                    measurement_unit=(
                        selected_unit
                    ),

                    # Sin frecuencia clara se guarda 0.0
                    # (el campo no admite nulos)
                    dominant_hz=(
                        analysis.get(
                            "dominant_hz"
                        )
                        or 0.0
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
    except IntegrityError:
        existing_measurement = (
            VibrationMeasurement.objects
            .filter(
                measurement_token=(
                    measurement_token
                )
            )
            .first()
        )

        if existing_measurement is None:
            raise

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

@login_required
@permission_required(
    "vibration.view_vibrationmeasurement",
    raise_exception=True,
)
def measurements_dashboard(request):
    """
    Muestra las mediciones vibratorias
    almacenadas en PostgreSQL.
    """

    # La lista no necesita el PDF (~165 KB) ni el análisis completo
    measurements = (
        VibrationMeasurement.objects
        .defer(
            "pdf_data",
            "analysis_data",
        )
        .order_by(
            "-created_at",
            "-id",
        )
    )

    page_obj = Paginator(
        measurements,
        MEASUREMENTS_PAGE_SIZE,
    ).get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "vibration/manage_measurements.html",
        {
            "measurements": page_obj,
            "page_obj": page_obj,
        },
    )


@login_required
@permission_required(
    "vibration.view_vibrationmeasurement",
    raise_exception=True,
)
def stored_measurement_pdf(
    request,
    measurement_id,
):
    """
    Descarga desde PostgreSQL el PDF
    perteneciente a una medición.
    """

    measurement = get_object_or_404(
        VibrationMeasurement,
        pk=measurement_id,
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
        content_type="application/pdf",
    )

    response[
        "X-SMAV-Folio"
    ] = measurement.folio

    return response