from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("catalogo/", views.catalogo_view, name="catalogo"),
    path('catalogo/', views.catalogo_view, name='catalogo'),
    path('catalogo/antivibratorios/', views.antivibratorios_view, name='antivibratorios'),
]