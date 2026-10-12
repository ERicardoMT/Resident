from django.urls import path

from . import api, views


urlpatterns = [
    path(
        "medicion/",
        views.measure,
        name="measure",
    ),
    path(
        "medicion/reporte-pdf/",
        views.measurement_pdf,
        name="measurement-pdf",
    ),

    # Administración de mediciones
    path(
        "dashboard/mediciones/",
        views.measurements_dashboard,
        name="measurements_dashboard",
    ),
    path(
        "dashboard/mediciones/<int:measurement_id>/pdf/",
        views.stored_measurement_pdf,
        name="stored_measurement_pdf",
    ),

    path(
        "api/",
        api.api_root,
        name="api-root",
    ),
    path(
        "api/analyze/",
        api.analyze,
        name="api-analyze",
    ),
]