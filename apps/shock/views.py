from django.shortcuts import render


def shock(request):
    return render(request, "shock/shock.html")
