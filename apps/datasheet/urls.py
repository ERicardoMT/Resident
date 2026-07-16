from django.urls import path

from . import views

urlpatterns = [
    path("datasheet/", views.datasheet, name="datasheet"),
]
