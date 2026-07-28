from django.urls import path

from . import views


urlpatterns = [
    path(
        "soportes-nivelador/",
        views.stops,
        name="stops",
    ),
]
