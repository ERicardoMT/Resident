from django.urls import path

from . import views


urlpatterns = [
    path(
        "soportes-nivelador/",
        views.stops,
        name="stops",
    ),

    path(
        "api/antivibratorios/recomendar/",
        views.recommend_antivibrator,
        name="recommend_antivibrator",
    ),
]