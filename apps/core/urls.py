from django.urls import path
from . import views

urlpatterns = [
    # --- Navegación Principal ---
    path("", views.home, name="home"),
    
    # --- Dashboard y Administración ---
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/usuarios/nuevo/", views.crear_usuario_view, name="crear_usuario"),
    path("dashboard/agregar-producto/", views.agregar_producto_view, name="agregar_producto"),
    
    # --- Catálogo y Categorías ---
    path("catalogo/", views.catalogo_view, name="catalogo"),
    path("catalogo/antivibratorios/", views.antivibratorios_view, name="antivibratorios"),
    path("catalogo/patas-niveladoras/", views.patas_niveladoras_view, name="patas_niveladoras"),
    path("catalogo/accionamiento/", views.accionamiento_view, name="accionamiento"),
    path("catalogo/mobiliario/", views.mobiliario_view, name="mobiliario"),
    
    # --- Detalle de Producto ---
    path("catalogo/producto/<str:nombre_producto>/", views.producto_detalle_view, name="producto_detalle"),
]