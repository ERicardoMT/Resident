from django.shortcuts import render


def measure(request):
    """Pantalla de medicion de frecuencia en tiempo real."""
    return render(request, "vibration/measure.html")
