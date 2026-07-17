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
            "icon": "datasheet",
            "title": "Documentación técnica",
            "subtitle": "Fichas, manuales y hojas de datos INAHER",
            "url_name": "datasheet",
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
    else:
        menu.append(
            {
                "icon": "login",
                "title": "Iniciar sesión",
                "subtitle": "Acceso al panel seguro",
                "url_name": "login",
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