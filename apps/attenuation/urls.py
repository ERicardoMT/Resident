from django.urls import path

from . import views

urlpatterns = [
    path("atenuacion/", views.attenuation, name="attenuation"),
]
