"""Endpoints de la API REST (Django REST Framework).

La medicion real de la vibracion se realiza en el navegador del dispositivo
movil (Android/iOS) con la API DeviceMotion. Estas muestras se envian aqui
para el analisis de senal en el servidor.
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .analysis import analyze_samples
from .serializers import AnalyzeRequestSerializer


@api_view(["GET"])
def api_root(request):
    """Descripcion de los endpoints disponibles."""
    return Response(
        {
            "name": "SMAV INAHER API",
"description": (
    "API del Sistema de Medición y Análisis Vibratorio de INAHER."
),
            "endpoints": {
                "analyze": {
                    "method": "POST",
                    "url": request.build_absolute_uri("/api/analyze/"),
                    "body": {
                        "samples": [
                            {"t": "ms", "x": "m/s^2", "y": "m/s^2", "z": "m/s^2"}
                        ]
                    },
                    "returns": [
                        "sample_rate_hz",
                        "sample_count",
                        "duration_s",
                        "rms_ms2",
                        "peak_ms2",
                        "crest",
                        "impacts",
                        "level",
                        "dominant_hz",
                        "dominant_rpm",
                        "frequency_status",
                        "frequency_message",
                        "frequency_note",
                        "f_min_hz",
                        "f_max_hz",
                        "rpm_placa",
                        "spectrum",
                    ],
                }
            },
        }
    )


@api_view(["POST"])
def analyze(request):
    """Recibe muestras del acelerómetro y devuelve métricas vibratorias y espectrales."""
    serializer = AnalyzeRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        result = analyze_samples(
            samples=serializer.validated_data["samples"],
            rpm_placa=serializer.validated_data.get("rpm_placa"),
            gravity_included=serializer.validated_data.get("gravity_included", False),
            user_agent=serializer.validated_data.get("user_agent", ""),
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(result, status=status.HTTP_200_OK)
