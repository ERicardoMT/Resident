from django.shortcuts import render


def stops(request):
    """
    Muestra la herramienta para seleccionar
    un soporte antivibratorio.
    """

    return render(
        request,
        "stops/stops.html",
    )