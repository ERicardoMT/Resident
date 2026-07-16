from django.urls import path

from . import api, views

urlpatterns = [
    path("medicion/", views.measure, name="measure"),
    path("api/", api.api_root, name="api-root"),
    path("api/analyze/", api.analyze, name="api-analyze"),
]
