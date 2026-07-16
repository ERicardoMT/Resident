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
                        "dominant_hz",
                        "rpm",
                        "sample_rate_hz",
                        "rms_ms2",
                        "rms_g",
                        "peak_ms2",
                        "peak_g",
                        "spectrum",
                    ],
                }
            },
        }
    )


@api_view(["POST"])
def analyze(request):
    """Recibe muestras del acelerometro y devuelve la frecuencia dominante."""
    serializer = AnalyzeRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        result = analyze_samples(serializer.validated_data["samples"])
    except ValueError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(result, status=status.HTTP_200_OK)
