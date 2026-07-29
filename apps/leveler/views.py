from django.shortcuts import render


def select_leveler(request):
    """
    Muestra una guía sencilla para elegir una familia
    de pie de nivelación.
    """

    return render(
        request,
        "leveler/select_leveler.html",
    )


def leveler(request):
    """
    Muestra el nivelador digital basado en los sensores
    de orientación del teléfono.
    """

    response = render(
        request,
        "leveler/leveler.html",
    )

    response.headers["Permissions-Policy"] = (
        "accelerometer=(self), gyroscope=(self)"
    )

    return response