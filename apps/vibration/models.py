import uuid

from django.db import models


class VibrationMeasurement(models.Model):
    """
    Medición vibratoria registrada desde SMAV.

    El PDF se conserva directamente en PostgreSQL
    junto con el folio y los resultados calculados.
    """

    UNIT_ACCELERATION = "acceleration"
    UNIT_VELOCITY = "velocity"

    UNIT_CHOICES = (
        (
            UNIT_ACCELERATION,
            "Aceleración vibratoria",
        ),
        (
            UNIT_VELOCITY,
            "Velocidad vibratoria",
        ),
    )

    measurement_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Identificador de medición",
    )

    folio = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        verbose_name="Folio",
    )

    measurement_unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default=UNIT_ACCELERATION,
        verbose_name="Unidad seleccionada",
    )

    dominant_hz = models.FloatField(
        default=0.0,
        verbose_name="Frecuencia dominante (Hz)",
    )

    rpm = models.FloatField(
        default=0.0,
        verbose_name="RPM",
    )

    sample_rate_hz = models.FloatField(
        default=0.0,
        verbose_name="Frecuencia de muestreo (Hz)",
    )

    sample_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Número de muestras",
    )

    duration_s = models.FloatField(
        default=0.0,
        verbose_name="Duración (s)",
    )

    rms_ms2 = models.FloatField(
        default=0.0,
        verbose_name="RMS aceleración (m/s²)",
    )

    rms_g = models.FloatField(
        default=0.0,
        verbose_name="RMS aceleración (g)",
    )

    peak_ms2 = models.FloatField(
        default=0.0,
        verbose_name="Pico aceleración (m/s²)",
    )

    peak_g = models.FloatField(
        default=0.0,
        verbose_name="Pico aceleración (g)",
    )

    velocity_rms_mms = models.FloatField(
        default=0.0,
        verbose_name="RMS velocidad (mm/s)",
    )

    velocity_peak_mms = models.FloatField(
        default=0.0,
        verbose_name="Pico velocidad (mm/s)",
    )

    analysis_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Resultado completo",
    )

    pdf_filename = models.CharField(
        max_length=255,
        verbose_name="Nombre del PDF",
    )

    pdf_data = models.BinaryField(
        verbose_name="Archivo PDF",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        ordering = (
            "-created_at",
            "-id",
        )

        verbose_name = (
            "Medición vibratoria"
        )

        verbose_name_plural = (
            "Mediciones vibratorias"
        )

    def __str__(self):
        return self.folio
