import math

from rest_framework import serializers


class SampleSerializer(serializers.Serializer):
    """Una muestra individual del acelerómetro."""

    t = serializers.FloatField(
        help_text="Marca de tiempo en milisegundos",
    )

    x = serializers.FloatField(
        required=False,
        default=0.0,
    )

    y = serializers.FloatField(
        required=False,
        default=0.0,
    )

    z = serializers.FloatField(
        required=False,
        default=0.0,
    )


class AnalyzeRequestSerializer(serializers.Serializer):
    """Cuerpo de la petición para /api/analyze/."""

    samples = SampleSerializer(
        many=True,
        allow_empty=False,
        min_length=8,
        max_length=5000,
    )

    rpm_placa = serializers.FloatField(
        required=False,
        allow_null=True,
        default=None,
        min_value=0.0,
        help_text="RPM nominal del motor indicada en la placa",
    )

    gravity_included = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Indica si el sensor incluye gravedad estática",
    )

    user_agent = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Identificador del navegador o dispositivo móvil",
    )

    def validate_samples(self, value):
        """
        Valida cantidad, valores numéricos y duración
        de la ventana enviada por el dispositivo.
        """

        # Comprobar que no existan NaN o infinitos.
        for index, sample in enumerate(value):
            for field_name in (
                "t",
                "x",
                "y",
                "z",
            ):
                number = sample[field_name]

                if not math.isfinite(number):
                    raise serializers.ValidationError(
                        (
                            f'La muestra {index + 1} contiene '
                            f'un valor inválido en "{field_name}".'
                        )
                    )

        times = [
            sample["t"]
            for sample in value
        ]

        duration_ms = max(times) - min(times)

        if duration_ms <= 0:
            raise serializers.ValidationError(
                (
                    "La duración de las muestras debe "
                    "ser mayor que cero."
                )
            )

        if duration_ms > 10_000:
            raise serializers.ValidationError(
                (
                    "La ventana de medición no puede "
                    "superar los 10 segundos."
                )
            )

        return value