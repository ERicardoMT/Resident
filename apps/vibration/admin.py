from django.contrib import admin

from .models import VibrationMeasurement


@admin.register(VibrationMeasurement)
class VibrationMeasurementAdmin(
    admin.ModelAdmin
):
    list_display = (
        "folio",
        "created_at",
        "dominant_hz",
        "rpm",
        "measurement_unit",
        "sample_count",
    )

    list_filter = (
        "measurement_unit",
        "created_at",
    )

    search_fields = (
        "folio",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "measurement_token",
        "folio",
        "measurement_unit",
        "dominant_hz",
        "rpm",
        "sample_rate_hz",
        "sample_count",
        "duration_s",
        "rms_ms2",
        "rms_g",
        "peak_ms2",
        "peak_g",
        "velocity_rms_mms",
        "velocity_peak_mms",
        "analysis_data",
        "pdf_filename",
        "created_at",
    )

    def has_add_permission(
        self,
        request,
    ):
        return False
