from django.shortcuts import render


def stops(request):
    return render(request, "stops/stops.html")
