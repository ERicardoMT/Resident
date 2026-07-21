from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("catalogo/", views.catalogo_view, name="catalogo"),
    path('catalogo/', views.catalogo_view, name='catalogo'),
    path('catalogo/antivibratorios/', views.antivibratorios_view, name='antivibratorios'),
    path('dashboard/agregar-producto/', views.agregar_producto_view, name='agregar_producto'),
    path('catalogo/producto/<str:nombre_producto>/', views.producto_detalle_view, name='producto_detalle'),
]