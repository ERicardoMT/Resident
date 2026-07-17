from django.shortcuts import render


def leveler(request):
    """Muestra el nivelador digital basado en sensores del dispositivo."""

    response = render(request, "leveler/leveler.html")

    # Permite utilizar acelerómetro y giroscopio desde el mismo sitio.
    response.headers["Permissions-Policy"] = (
        "accelerometer=(self), gyroscope=(self)"
    )

    return response