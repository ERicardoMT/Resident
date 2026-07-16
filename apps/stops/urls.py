from django.urls import path

from . import views

urlpatterns = [
    path("topes/", views.stops, name="stops"),
]
