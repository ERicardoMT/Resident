from django.shortcuts import render


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

    if request.user.is_authenticated:
        menu.append(
            {
                "icon": "logout",
                "title": "Cerrar sesión",
                "subtitle": "Salir de la sesión activa",
                "url_name": "logout",
                "available": True,
            }
        )

    return render(request, "core/home.html", {"menu": menu})


def catalogo_view(request):
    """Muestra las categorías principales del catálogo INAHER."""

    categorias = [
        {
            "name": "Antivibratorios",
            "description": "Elementos para aislamiento y control de vibraciones.",
            "icon": "vibration",
        },
        {
            "name": "Patas niveladoras",
            "description": "Soluciones de apoyo, ajuste y nivelación industrial.",
            "icon": "leveling",
        },
        {
            "name": "Elementos de accionamiento y maniobra",
            "description": "Componentes para control y operación de maquinaria.",
            "icon": "control",
        },
        {
            "name": "Niveladores para mobiliario",
            "description": "Elementos de regulación para muebles y estructuras.",
            "icon": "furniture",
        },
    ]

    return render(
        request,
        "core/catalogo.html",
        {"categorias": categorias},
    )


def antivibratorios_view(request):
    productos = [
        # --- COLGANTES ANTIVIBRACIÓN ---
        {'nombre': 'COLGANTE ANTIVIBRACIÓN DE CAUCHO LÍNEA CDC-2 PARA 100 KG', 'precio': 'Cotizar', 'categoria': 'colgantes', 'badge': None},
        {'nombre': 'COLGANTE ANTIVIBRACIÓN DE RESORTE LÍNEA CDR-2 PARA 120 KG', 'precio': 'Cotizar', 'categoria': 'colgantes', 'badge': None},
        {'nombre': 'COLGANTE ANTIVIBRATORIO LÍNEA CIR PARA 100 KG', 'precio': 'Cotizar', 'categoria': 'colgantes', 'badge': 'Nuevo 2024'},
        
        # --- NIVELADORES ANTIVIBRACIÓN PARA MAQUINARIA ---
        {'nombre': 'NIVELADOR ANTIVIBRATORIO LÍNEA IVH-12 PARA 4500 KG', 'precio': 'Cotizar', 'categoria': 'niveladores_maq', 'badge': None},
        {'nombre': 'NIVELADOR ANTIVIBRATORIO LÍNEA IVH-3 PARA 300 KG', 'precio': 'Cotizar', 'categoria': 'niveladores_maq', 'badge': None},
        {'nombre': 'Nivelador Antivibratorio Línea IVH-4 PARA 850 KG', 'precio': 'Cotizar', 'categoria': 'niveladores_maq', 'badge': 'Top 10'},
        {'nombre': 'NIVELADOR ANTIVIBRATORIO LÍNEA IVH-6 PARA 1800 KG', 'precio': 'Cotizar', 'categoria': 'niveladores_maq', 'badge': None},
        {'nombre': 'NIVELADOR ANTIVIBRATORIO LÍNEA IVH-9 PARA 3000 KG', 'precio': 'Cotizar', 'categoria': 'niveladores_maq', 'badge': None},
        
        # --- PIES ANTIVIBRACIÓN ---
        {'nombre': 'NIVELADOR ANTIVIBRATORIO LÍNEA CET DE 350 A 900 KG', 'precio': 'Cotizar', 'categoria': 'pies', 'badge': 'Nuevo 2024'},
        
        # --- SOPORTES ANTIVIBRACIÓN CON ANCLAJE AL PISO ---
        {'nombre': 'ANTIVIBRATORIO CON FIJACIÓN AL PISO LONG LIFE PARA 700 KG', 'precio': 'Cotizar', 'categoria': 'soportes_piso', 'badge': None},
        {'nombre': 'ANTIVIBRATORIO PARA MAQUINARIA DE RESORTE LÍNEA HST PARA 200 KG', 'precio': 'Cotizar', 'categoria': 'soportes_piso', 'badge': None},
        {'nombre': 'ANTIVIBRATORIO PARA MAQUINARIA DE RESORTE LÍNEA RDM-350 PARA 350 KG', 'precio': 'Cotizar', 'categoria': 'soportes_piso', 'badge': None},
        {'nombre': 'ANTIVIBRATORIO PARA MAQUINARIA DE RESORTE LÍNEA RDM-600 PARA 600 KG', 'precio': 'Cotizar', 'categoria': 'soportes_piso', 'badge': None},
        {'nombre': 'SOPORTE ANTIVIBRACIÓN CON FIJACIÓN LÍNEA REBO PARA 250 KG', 'precio': 'Cotizar', 'categoria': 'soportes_piso', 'badge': None},
        
        # --- TACONES ANTIVIBRACIÓN ---
        {'nombre': 'ANTIVIBRATORIO HEMBRA-HEMBRA LÍNEA HFF PARA 12 KG A 150 KG', 'precio': 'Cotizar', 'categoria': 'tacones', 'badge': None},
        {'nombre': 'SOPORTE ANTIVIBRACIÓN LÍNEA MSH-880 PARA 600 KG', 'precio': 'Cotizar', 'categoria': 'tacones', 'badge': None},
        {'nombre': 'SOPORTE ANTIVIBRACIÓN LÍNEA MXI-700 PARA 400 KG', 'precio': 'Cotizar', 'categoria': 'tacones', 'badge': None},
        {'nombre': 'SOPORTE ANTIVIBRATORIO LÍNEA SBS-80 PARA 450 KG', 'precio': 'Cotizar', 'categoria': 'tacones', 'badge': None},
        {'nombre': 'SOPORTE ANTIVIBRATORIO SBS-120 PARA 900 KG', 'precio': 'Cotizar', 'categoria': 'tacones', 'badge': 'Nuevo 2024'},
    ]
    return render(request, 'core/antivibratorios.html', {'productos': productos})