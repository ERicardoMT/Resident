from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/usuarios/",views.usuarios_dashboard_view,name="usuarios_dashboard",),
    path("dashboard/usuarios/<int:user_id>/eliminar/",views.eliminar_usuario_view,name="eliminar_usuario",),
    path("dashboard/productos/",views.productos_dashboard_view,name="productos_dashboard",),
    path("dashboard/productos/<int:product_id>/eliminar/",views.eliminar_producto_view,name="eliminar_producto",),
    path("dashboard/administrar-catalogo/", views.administrar_catalogo_view, name="administrar_catalogo"),
    path("dashboard/editar/<int:id>/", views.editar_producto_view, name="editar_producto"),
    path("dashboard/usuarios/nuevo/", views.crear_usuario_view, name="crear_usuario"),
    path("dashboard/agregar-producto/", views.agregar_producto_view, name="agregar_producto"),
    path("dashboard/eliminar/<int:id>/", views.eliminar_producto_view, name="eliminar_producto"),
    
    path("catalogo/", views.catalogo_view, name="catalogo"),
    path("catalogo/antivibratorios/", views.antivibratorios_view, name="antivibratorios"),
    path("catalogo/producto/<str:nombre_producto>/", views.producto_detalle_view, name="producto_detalle"),

    # --- ESTAS SON LAS RUTAS QUE FALTAN Y CAUSAN EL ERROR ---
    path("catalogo/patas-niveladoras/", views.patas_niveladoras_view, name="patas_niveladoras"),
    path("catalogo/accionamiento/", views.accionamiento_view, name="accionamiento"),
    path("catalogo/mobiliario/", views.mobiliario_view, name="mobiliario"),
]