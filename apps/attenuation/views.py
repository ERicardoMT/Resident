from django.shortcuts import render


def attenuation(request):
    return render(request, "attenuation/attenuation.html")
