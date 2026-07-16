from django.shortcuts import render


def datasheet(request):
    return render(request, "datasheet/datasheet.html")
