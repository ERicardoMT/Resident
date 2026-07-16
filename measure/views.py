from django.shortcuts import render


def home(request):
    """Menu principal estilo PaulstraSoft Mobile."""
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
    return render(request, "measure/home.html", {"menu": menu})


def measure(request):
    """Pantalla de medicion de frecuencia en tiempo real."""
    return render(request, "measure/measure.html")


def attenuation(request):
    return render(request, "measure/attenuation.html")


def shock(request):
    return render(request, "measure/shock.html")


def stops(request):
    return render(request, "measure/stops.html")


def datasheet(request):
    return render(request, "measure/datasheet.html")
