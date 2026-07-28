from django.shortcuts import render


def stops(request):
    """
    Muestra la selección de soporte y el nivelador digital.
    """

    response = render(
        request,
        "stops/stops.html",
    )

    response.headers["Permissions-Policy"] = (
        "accelerometer=(self), gyroscope=(self)"
    )

    return response
