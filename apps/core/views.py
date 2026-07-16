from django.shortcuts import render


def home(request):
    """Menu principal del proyecto."""
    menu = [
        {
            "icon": "hz",
            "title": "Medicion vibratoria y preseleccion",
            "subtitle": "Mide la frecuencia (Hz) con el acelerometro",
            "url_name": "measure",
            "available": True,
        },
        {
            "icon": "attenuation",
            "title": "Atenuacion vibratoria",
            "subtitle": "Transmisibilidad segun frecuencia",
            "url_name": "attenuation",
            "available": True,
        },
        {
            'title': 'Catálogo de productos',
            'subtitle': 'Componentes y niveladores',
            'icon': 'catalog',
            'url_name': 'catalogo'
        },
        {
            "icon": "shock",
            "title": "Calculo de respuesta a choque",
            "subtitle": "Espectro de respuesta a impacto",
            "url_name": "shock",
            "available": True,
        },
        {
            "icon": "stops",
            "title": "Calculo de topes",
            "subtitle": "Dimensionado de topes elasticos",
            "url_name": "stops",
            "available": True,
        },
        {
            "icon": "datasheet",
            "title": "Hojas de datos de productos",
            "subtitle": "Documentacion tecnica",
            "url_name": "datasheet",
            "available": True,
        },     
    ]
    return render(request, "core/home.html", {"menu": menu})

def catalogo_view(request):
    return render(request, 'core/catalogo.html')