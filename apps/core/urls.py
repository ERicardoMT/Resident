from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.home,
        name="home",
    ),

    # Dashboard principal
    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),

    # Administración de usuarios
    path(
        "dashboard/usuarios/",
        views.usuarios_dashboard_view,
        name="usuarios_dashboard",
    ),
    path(
        "dashboard/usuarios/nuevo/",
        views.crear_usuario_view,
        name="crear_usuario",
    ),
    path(
        "dashboard/usuarios/<int:user_id>/eliminar/",
        views.eliminar_usuario_view,
        name="eliminar_usuario",
    ),

    # Administración de productos
    path(
        "dashboard/productos/",
        views.productos_dashboard_view,
        name="productos_dashboard",
    ),
    path(
        "dashboard/agregar-producto/",
        views.agregar_producto_view,
        name="agregar_producto",
    ),
    path(
        "dashboard/productos/<int:product_id>/editar/",
        views.editar_producto_view,
        name="editar_producto",
    ),
    path(
        "dashboard/productos/<int:product_id>/eliminar/",
        views.eliminar_producto_view,
        name="eliminar_producto",
    ),

    
    # Catálogo público
    path(
        "catalogo/",
        views.catalogo_view,
        name="catalogo",
    ),
    path(
        "catalogo/antivibratorios/",
        views.antivibratorios_view,
        name="antivibratorios",
    ),
    path(
        "catalogo/patas-niveladoras/",
        views.patas_niveladoras_view,
        name="patas_niveladoras",
    ),
    path(
        "catalogo/accionamiento/",
        views.accionamiento_view,
        name="accionamiento",
    ),
    path(
        "catalogo/mobiliario/",
        views.mobiliario_view,
        name="mobiliario",
    ),
    path(
        "catalogo/producto/<str:nombre_producto>/",
        views.producto_detalle_view,
        name="producto_detalle",
    ),
]