from rest_framework import serializers


class SampleSerializer(serializers.Serializer):
    """Una muestra individual del acelerometro."""

    t = serializers.FloatField(help_text="Marca de tiempo en milisegundos")
    x = serializers.FloatField(required=False, default=0.0)
    y = serializers.FloatField(required=False, default=0.0)
    z = serializers.FloatField(required=False, default=0.0)


class AnalyzeRequestSerializer(serializers.Serializer):
    """Cuerpo de la peticion para /api/analyze/."""

    samples = SampleSerializer(many=True)

    def validate_samples(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Se necesitan al menos 8 muestras para analizar."
            )
        return value
