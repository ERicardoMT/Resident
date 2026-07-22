from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import SMAVUserCreationForm
from .models import CatalogItem


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
            "icon": "shock",
            "title": "Respuesta a choque",
            "subtitle": "Evaluación de impactos y respuesta dinámica",
            "url_name": "shock",
            "available": True,
        },
        {
            "icon": "stops",
            "title": "Selección de soportes y topes",
            "subtitle": "Dimensionamiento de elementos elásticos",
            "url_name": "stops",
            "available": True,
        },
        {
            "icon": "leveler",
            "title": "Nivelador digital",
            "subtitle": "Mide inclinación y nivelación con los sensores del teléfono",
            "url_name": "leveler",
            "available": True,
        },
    ]
    
    return render(request, "core/home.html", {"menu": menu})


@login_required
def dashboard(request):
    """Panel de gestión para usuarios y catálogo."""

    user_model = get_user_model()

    catalog_count = CatalogItem.objects.filter(
        is_active=True
    ).count()

    stats = [
        {
            "label": "Usuarios",
            "num": user_model.objects.count(),
            "hint": "Cuentas registradas",
        },
        {
            "label": "Catálogo",
            "num": catalog_count,
            "hint": "Elementos activos",
        },
        {
            "label": "Sesión",
            "num": "Activa",
            "hint": (
                request.user.get_username()
                or "Usuario autenticado"
            ),
        },
    ]

    actions = [
        {
            "icon": "users",
            "title": "Crear usuario",
            "subtitle": (
                "Registrar una cuenta desde el panel SMAV"
            ),
            "url": reverse("crear_usuario"),
        },
        {
            "icon": "catalog",
            "title": "Agregar al catálogo",
            "subtitle": (
                "Registrar nuevos elementos del catálogo"
            ),
            "url": reverse("agregar_producto"),
        },
        {
            "icon": "catalog",
            "title": "Ver catálogo",
            "subtitle": (
                "Revisar las familias y productos publicados"
            ),
            "url": reverse("catalogo"),
        },
    ]

    recent_items = CatalogItem.objects.filter(
        is_active=True
    ).order_by('-id')[:6]

    return render(
        request,
        "core/dashboard.html",
        {
            "stats": stats,
            "actions": actions,
            "recent_items": recent_items,
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
    productos = [
        {'nombre': 'COLGANTE ANTIVIBRACIÓN DE CAUCHO LÍNEA CDC-2 PARA 100 KG', 'precio': 'Cotizar', 'categoria': 'colgantes', 'badge': None},
        {'nombre': 'COLGANTE ANTIVIBRACIÓN DE RESORTE LÍNEA CDR-2 PARA 120 KG', 'precio': 'Cotizar', 'categoria': 'colgantes', 'badge': None},
        {'nombre': 'COLGANTE ANTIVIBRATORIO LÍNEA CIR PARA 100 KG', 'precio': 'Cotizar', 'categoria': 'colgantes', 'badge': 'Nuevo 2024'},
        {'nombre': 'NIVELADOR ANTIVIBRATORIO LÍNEA IVH-12 PARA 4500 KG', 'precio': 'Cotizar', 'categoria': 'niveladores_maq', 'badge': None},
        {'nombre': 'NIVELADOR ANTIVIBRATORIO LÍNEA IVH-3 PARA 300 KG', 'precio': 'Cotizar', 'categoria': 'niveladores_maq', 'badge': None},
        {'nombre': 'Nivelador Antivibratorio Línea IVH-4 PARA 850 KG', 'precio': 'Cotizar', 'categoria': 'niveladores_maq', 'badge': 'Top 10'},
        {'nombre': 'NIVELADOR ANTIVIBRATORIO LÍNEA IVH-6 PARA 1800 KG', 'precio': 'Cotizar', 'categoria': 'niveladores_maq', 'badge': None},
        {'nombre': 'NIVELADOR ANTIVIBRATORIO LÍNEA IVH-9 PARA 3000 KG', 'precio': 'Cotizar', 'categoria': 'niveladores_maq', 'badge': None},
        {'nombre': 'NIVELADOR ANTIVIBRATORIO LÍNEA CET DE 350 A 900 KG', 'precio': 'Cotizar', 'categoria': 'pies', 'badge': 'Nuevo 2024'},
        {'nombre': 'ANTIVIBRATORIO CON FIJACIÓN AL PISO LONG LIFE PARA 700 KG', 'precio': 'Cotizar', 'categoria': 'soportes_piso', 'badge': None},
        {'nombre': 'ANTIVIBRATORIO PARA MAQUINARIA DE RESORTE LÍNEA HST PARA 200 KG', 'precio': 'Cotizar', 'categoria': 'soportes_piso', 'badge': None},
        {'nombre': 'ANTIVIBRATORIO PARA MAQUINARIA DE RESORTE LÍNEA RDM-350 PARA 350 KG', 'precio': 'Cotizar', 'categoria': 'soportes_piso', 'badge': None},
        {'nombre': 'ANTIVIBRATORIO PARA MAQUINARIA DE RESORTE LÍNEA RDM-600 PARA 600 KG', 'precio': 'Cotizar', 'categoria': 'soportes_piso', 'badge': None},
        {'nombre': 'SOPORTE ANTIVIBRACIÓN CON FIJACIÓN LÍNEA REBO PARA 250 KG', 'precio': 'Cotizar', 'categoria': 'soportes_piso', 'badge': None},
        {'nombre': 'ANTIVIBRATORIO HEMBRA-HEMBRA LÍNEA HFF PARA 12 KG A 150 KG', 'precio': 'Cotizar', 'categoria': 'tacones', 'badge': None},
        {'nombre': 'SOPORTE ANTIVIBRACIÓN LÍNEA MSH-880 PARA 600 KG', 'precio': 'Cotizar', 'categoria': 'tacones', 'badge': None},
        {'nombre': 'SOPORTE ANTIVIBRACIÓN LÍNEA MXI-700 PARA 400 KG', 'precio': 'Cotizar', 'categoria': 'tacones', 'badge': None},
        {'nombre': 'SOPORTE ANTIVIBRATORIO LÍNEA SBS-80 PARA 450 KG', 'precio': 'Cotizar', 'categoria': 'tacones', 'badge': None},
        {'nombre': 'SOPORTE ANTIVIBRATORIO SBS-120 PARA 900 KG', 'precio': 'Cotizar', 'categoria': 'tacones', 'badge': 'Nuevo 2024'},
    ]

    categorias_validas = ['colgantes', 'niveladores_maq', 'pies', 'soportes_piso', 'tacones']
    nuevos_productos = CatalogItem.objects.filter(category__in=categorias_validas).order_by('-id')

    for item in nuevos_productos:
        productos.insert(0, {
            'nombre': item.name,
            'precio': item.price_label,
            'categoria': item.category,
            'badge': item.badge,
            'imagen': item.image  # Asegura que la plantilla HTML lea .url
        })

    return render(request, 'core/antivibratorios.html', {'productos': productos})


def patas_niveladoras_view(request):
    # Lista de todas las posibles formas en las que se puede guardar esta categoría
    categorias_validas = [
        'Patas niveladoras', 'patas_niveladoras', 'patas',
        'Antiderrapante', 'antiderrapante', 'ANTIDERRAPANTE',
        'Alta resistencia', 'alta_resistencia', 'ALTA RESISTENCIA',
        'Anclaje al piso', 'anclaje_piso', 'ANCLAJE AL PISO',
        'Antivibracion', 'antivibracion', 'ANTIVIBRACION',
        'Con rotula', 'con_rotula', 'CON ROTULA',
        'Uso rudo', 'uso_rudo', 'USO RUDO'
    ]
    productos = CatalogItem.objects.filter(category__in=categorias_validas).order_by('-id')
    return render(request, 'core/patas.html', {'productos': productos})

def accionamiento_view(request):
    # Lista abierta para capturar cualquier variación con la que se guarde la categoría
    categorias_validas = [
        'Elementos de accionamiento y maniobra', 
        'elementos de accionamiento y maniobra', 
        'Accionamiento', 
        'accionamiento', 
        'ACCIONAMIENTO', 
        'Maniobra', 
        'maniobra'
    ]
    productos = CatalogItem.objects.filter(category__in=categorias_validas).order_by('-id')
    return render(request, 'core/accionamiento.html', {'productos': productos})

def mobiliario_view(request):
    categorias_validas = [
        'Niveladores para mobiliario', 
        'niveladores para mobiliario', 
        'Mobiliario', 
        'mobiliario', 
        'MOBILIARIO'
    ]
    productos = CatalogItem.objects.filter(category__in=categorias_validas).order_by('-id')
    return render(request, 'core/mobiliario.html', {'productos': productos})


@login_required
@permission_required(
    "core.add_catalogitem",
    raise_exception=True,
)
def agregar_producto_view(request):
    if request.method == "POST":
        nombre = request.POST.get("name")
        categoria = request.POST.get("category")
        descripcion = request.POST.get("description", "")
        precio = request.POST.get("price_label", "Cotizar")
        badge = request.POST.get("badge", "")

        # Recibir archivos multimedia usando request.FILES
        imagen = request.FILES.get("image")
        modelo_3d = request.FILES.get("model_3d")

        nuevo_item = CatalogItem(
            name=nombre,
            category=categoria,
            description=descripcion,
            price_label=precio,
            badge=badge,
            image=imagen,
            model_3d=modelo_3d,
            is_active=True,
            sort_order=0,
        )

        nuevo_item.save()
        return redirect('dashboard')
        
    return render(request, 'core/add_product.html')


def producto_detalle_view(request, nombre_producto):
    # 1. Buscar en la base de datos de PostgreSQL
    producto_encontrado = CatalogItem.objects.filter(name=nombre_producto).first()

    # 2. Respaldo para los productos estáticos antiguos
    if not producto_encontrado:
        productos_estaticos = [
            {'nombre': 'COLGANTE ANTIVIBRACIÓN DE CAUCHO LÍNEA CDC-2 PARA 100 KG', 'precio': 'Cotizar', 'categoria': 'colgantes', 'badge': None, 'descripcion': 'Descripción genérica...'},
        ]
        
        for prod in productos_estaticos:
            if prod['nombre'] == nombre_producto:
                class ProductoFalso:
                    pass
                producto_encontrado = ProductoFalso()
                producto_encontrado.name = prod['nombre']
                producto_encontrado.price_label = prod['precio']
                producto_encontrado.category = prod['categoria']
                producto_encontrado.badge = prod['badge']
                producto_encontrado.description = prod['descripcion']
                producto_encontrado.image = None
                break

    return render(request, 'core/producto_detalle.html', {'producto': producto_encontrado})