from django.urls import path

from . import api, views

urlpatterns = [
    # Paginas
    path("", views.home, name="home"),
    path("medicion/", views.measure, name="measure"),
    path("atenuacion/", views.attenuation, name="attenuation"),
    path("choque/", views.shock, name="shock"),
    path("topes/", views.stops, name="stops"),
    path("datasheet/", views.datasheet, name="datasheet"),
    # API REST
    path("api/", api.api_root, name="api-root"),
    path("api/analyze/", api.analyze, name="api-analyze"),
]
