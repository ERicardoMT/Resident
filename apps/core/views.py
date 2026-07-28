from urllib import request

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse

from .forms import (
    CatalogItemForm,
    SMAVUserCreationForm,
)
from .models import (
    CatalogCategory,
    CatalogItem,
)
from pathlib import Path


def home(request):
    """Muestra el panel principal de SMAV INAHER."""

    menu = [
        {
            "icon": "hz",
            "title": "Medición vibratoria",
            "subtitle": "Frecuencia, RPM, aceleración y espectro FFT",
            "url_name": "measure",
            "available": True,
        },
        {
            "icon": "attenuation",
            "title": "Atenuación y aislamiento",
            "subtitle": "Transmisibilidad según la frecuencia",
            "url_name": "attenuation",
            "available": True,
        },
        {
            "icon": "catalog",
            "title": "Catálogo de productos",
            "subtitle": "Antivibratorios, niveladores y componentes",
            "url_name": "catalogo",
            "available": True,
        },
        {
            "icon": "stops",
            "title": "Selección de soporte y Nivelador",
            "subtitle": (
                "Dimensionamiento de soportes y "
                "nivelación con sensores"
            ),
            "url_name": "stops",
            "available": True,
        },
    ]
    
    return render(request, "core/home.html", {"menu": menu})


@login_required
def dashboard(request):
    """Panel de gestión para usuarios y catálogo."""

    user_model = get_user_model()

    can_view_users = request.user.has_perm(
        "auth.view_user"
    )

    can_view_catalog = request.user.has_perm(
        "core.view_catalogitem"
    )

    catalog_count = CatalogItem.objects.filter(
        is_active=True
    ).count()

    stats = [
        {
            "label": "Usuarios",
            "num": user_model.objects.count(),
            "hint": "Cuentas registradas",
            "url": (
                reverse("usuarios_dashboard")
                if can_view_users
                else ""
            ),
        },
        {
            "label": "Catálogo",
            "num": catalog_count,
            "hint": "Elementos activos",
            "url": (
                reverse("productos_dashboard")
                if can_view_catalog
                else ""
            ),
        },
        {
            "label": "Sesión",
            "num": "Activa",
            "hint": (
                request.user.get_username()
                or "Usuario autenticado"
            ),
            "url": "",
        },
    ]

    return render(
        request,
        "core/dashboard.html",
        {
            "stats": stats,
            "can_add_users": request.user.has_perm(
                "auth.add_user"
            ),
            "can_add_catalog": request.user.has_perm(
                "core.add_catalogitem"
            ),
        },
    )


@login_required
@permission_required(
    "auth.view_user",
    raise_exception=True,
)
def usuarios_dashboard_view(request):
    """Muestra las cuentas registradas en SMAV."""

    user_model = get_user_model()

    usuarios = user_model.objects.all().order_by(
        "-is_superuser",
        "-is_staff",
        "username",
    )

    return render(
        request,
        "core/manage_users.html",
        {
            "usuarios": usuarios,
            "can_add_users": request.user.has_perm(
                "auth.add_user"
            ),
            "can_delete_users": request.user.has_perm(
                "auth.delete_user"
            ),
        },
    )


@login_required
@permission_required(
    "auth.delete_user",
    raise_exception=True,
)
@require_POST
def eliminar_usuario_view(request, user_id):
    """Elimina una cuenta con comprobaciones de seguridad."""

    user_model = get_user_model()

    usuario = get_object_or_404(
        user_model,
        pk=user_id,
    )

    if usuario.pk == request.user.pk:
        messages.error(
            request,
            "No puedes eliminar la cuenta con la que "
            "tienes iniciada la sesión.",
        )
        return redirect("usuarios_dashboard")

    if usuario.is_superuser and not request.user.is_superuser:
        messages.error(
            request,
            "Solo un superusuario puede eliminar "
            "a otro superusuario.",
        )
        return redirect("usuarios_dashboard")

    active_superusers = user_model.objects.filter(
        is_superuser=True,
        is_active=True,
    ).count()

    if (
        usuario.is_superuser
        and usuario.is_active
        and active_superusers <= 1
    ):
        messages.error(
            request,
            "No se puede eliminar al último "
            "superusuario activo.",
        )
        return redirect("usuarios_dashboard")

    username = usuario.get_username()
    usuario.delete()

    messages.success(
        request,
        f'El usuario "{username}" fue eliminado.',
    )

    return redirect("usuarios_dashboard")


@login_required
@permission_required(
    "core.view_catalogitem",
    raise_exception=True,
)
@login_required
@permission_required(
    "core.view_catalogitem",
    raise_exception=True,
)
def productos_dashboard_view(request):
    """Muestra los productos registrados en la base de datos."""

    productos = CatalogItem.objects.all().order_by(
        "-created_at",
        "-id",
    )

    return render(
        request,
        "core/manage_products.html",
        {
            "productos": productos,
            "can_add_catalog": request.user.has_perm(
                "core.add_catalogitem"
            ),
            "can_change_catalog": request.user.has_perm(
                "core.change_catalogitem"
            ),
            "can_delete_catalog": request.user.has_perm(
                "core.delete_catalogitem"
            ),
        },
    )


@login_required
@permission_required(
    "core.delete_catalogitem",
    raise_exception=True,
)
@require_POST
def eliminar_producto_view(request, product_id):
    producto = get_object_or_404(
        CatalogItem,
        pk=product_id,
    )

    product_name = producto.name

    for field_name in (
        "image",
        "model_3d",
        "ar_model",
    ):
        archivo = getattr(
            producto,
            field_name,
            None,
        )

        if archivo and archivo.name:
            archivo.delete(save=False)

    producto.delete()

    messages.success(
        request,
        f'El producto "{product_name}" fue eliminado.',
    )

    return redirect("productos_dashboard")

@login_required
@permission_required(
    "auth.add_user",
    raise_exception=True,
)
def crear_usuario_view(request):
    """Crea usuarios desde una interfaz integrada con SMAV."""

    can_assign_staff = request.user.is_superuser

    if request.method == "POST":
        form = SMAVUserCreationForm(
            request.POST,
            can_assign_staff=can_assign_staff,
        )

        if form.is_valid():
            new_user = form.save()

            messages.success(
                request,
                (
                    f'El usuario "{new_user.username}" '
                    "se creó correctamente."
                ),
            )

            return redirect("dashboard")
    else:
        form = SMAVUserCreationForm(
            can_assign_staff=can_assign_staff,
        )

    return render(
        request,
        "core/create_user.html",
        {
            "form": form,
            "can_assign_staff": can_assign_staff,
        },
    )


def catalogo_view(request):
    """Muestra las categorías principales del catálogo INAHER."""

    categorias = [
        {
            "name": "Antivibratorios",
            "description": "Elementos para aislamiento y control de vibraciones.",
            "icon": "vibration",
            "url_name": "antivibratorios", # <-- Ya conectada
        },
        {
            "name": "Patas niveladoras",
            "description": "Soluciones de apoyo, ajuste y nivelación industrial.",
            "icon": "leveling",
            "url_name": "patas_niveladoras", # <-- Ajustar si en tu urls.py se llama distinto (ej. "patas")
        },
        {
            "name": "Elementos de accionamiento y maniobra",
            "description": "Componentes para control y operación de maquinaria.",
            "icon": "control",
            "url_name": "accionamiento", 
        },
        {
            "name": "Niveladores para mobiliario",
            "description": "Elementos de regulación para muebles y estructuras.",
            "icon": "furniture",
            "url_name": "mobiliario", 
        },
    ]

    catalog_items = CatalogItem.objects.filter(is_active=True).order_by('-id')

    return render(
        request,
        "core/catalogo.html",
        {"categorias": categorias, "catalog_items": catalog_items},
    )

def antivibratorios_view(request):
    productos = CatalogItem.objects.filter(
        category=CatalogCategory.ANTIVIBRATORIOS,
        is_active=True,
    ).order_by("-id")

    return render(
        request,
        "core/antivibratorios.html",
        {
            "productos": productos,
        },
    )

def patas_niveladoras_view(request):
    productos = CatalogItem.objects.filter(
        category=CatalogCategory.PATAS_NIVELADORAS,
        is_active=True,
    ).order_by("-id")

    return render(
        request,
        "core/patas.html",
        {
            "productos": productos,
        },
    )

def accionamiento_view(request):
    productos = CatalogItem.objects.filter(
        category=CatalogCategory.ACCIONAMIENTO,
        is_active=True,
    ).order_by("-id")

    return render(
        request,
        "core/accionamiento.html",
        {
            "productos": productos,
        },
    )

def mobiliario_view(request):
    productos = CatalogItem.objects.filter(
        category=CatalogCategory.MOBILIARIO,
        is_active=True,
    ).order_by("-id")

    return render(
        request,
        "core/mobiliario.html",
        {
            "productos": productos,
        },
    )


@login_required
@permission_required(
    "core.add_catalogitem",
    raise_exception=True,
)
def agregar_producto_view(request):
    """Crea un producto usando CatalogItemForm."""

    if request.method == "POST":
        form = CatalogItemForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            producto = form.save()

            messages.success(
                request,
                (
                    f'El producto "{producto.name}" '
                    "se guardó correctamente."
                ),
            )

            return redirect("productos_dashboard")
    else:
        form = CatalogItemForm()

    return render(
        request,
        "core/add_product.html",
        {
            "form": form,
        },
    )

def producto_detalle_view(request, nombre_producto):
    producto_encontrado = CatalogItem.objects.filter(
        name=nombre_producto,
        is_active=True,
    ).first()

    # Respaldo temporal para productos estáticos antiguos.
    if not producto_encontrado:
        productos_estaticos = [
            {
                "nombre": (
                    "COLGANTE ANTIVIBRACIÓN DE CAUCHO "
                    "LÍNEA CDC-2 PARA 100 KG"
                ),
                "precio": "Cotizar",
                "categoria": "colgantes",
                "badge": None,
                "descripcion": "Descripción genérica...",
            },
        ]

        for producto in productos_estaticos:
            if producto["nombre"] == nombre_producto:
                class ProductoFalso:
                    pass

                producto_encontrado = ProductoFalso()
                producto_encontrado.name = producto["nombre"]
                producto_encontrado.price_label = producto["precio"]
                producto_encontrado.category = producto["categoria"]
                producto_encontrado.badge = producto["badge"]
                producto_encontrado.description = producto["descripcion"]
                producto_encontrado.image = None
                producto_encontrado.model_3d = None
                producto_encontrado.ar_model = None
                producto_encontrado.model_url = ""
                break

    return render(
        request,
        "core/producto_detalle.html",
        {
            "producto": producto_encontrado,
        },
    )



@login_required
@permission_required(
    "core.change_catalogitem",
    raise_exception=True,
)
def editar_producto_view(request, product_id):
    """Edita un producto usando CatalogItemForm."""

    producto = get_object_or_404(
        CatalogItem,
        pk=product_id,
    )

    old_files = {
        "image": (
            producto.image.name
            if producto.image
            else ""
        ),
        "model_3d": (
            producto.model_3d.name
            if producto.model_3d
            else ""
        ),
        "ar_model": (
            producto.ar_model.name
            if producto.ar_model
            else ""
        ),
    }

    if request.method == "POST":
        form = CatalogItemForm(
            request.POST,
            request.FILES,
            instance=producto,
        )

        if form.is_valid():
            producto_actualizado = form.save()

            for field_name, old_name in old_files.items():
                new_file = getattr(
                    producto_actualizado,
                    field_name,
                )

                new_name = (
                    new_file.name
                    if new_file
                    else ""
                )

                if old_name and old_name != new_name:
                    model_field = (
                        producto_actualizado
                        ._meta
                        .get_field(field_name)
                    )

                    model_field.storage.delete(
                        old_name
                    )

            messages.success(
                request,
                (
                    f'El producto '
                    f'"{producto_actualizado.name}" '
                    "se actualizó correctamente."
                ),
            )

            return redirect("productos_dashboard")
    else:
        form = CatalogItemForm(
            instance=producto,
        )

    return render(
        request,
        "core/editar_producto.html",
        {
            "producto": producto,
            "form": form,
        },
    )