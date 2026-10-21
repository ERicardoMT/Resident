from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from apps.core.auth_views import RateLimitedLoginView


urlpatterns = [
    path("admin/", admin.site.urls),
    # Antes de auth.urls: el login con límite de intentos reemplaza al de Django
    path("accounts/login/", RateLimitedLoginView.as_view(), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.attenuation.urls")),
    path("", include("apps.vibration.urls")),
    path("", include("apps.stops.urls")),
    path("", include("apps.leveler.urls")),
]


# Archivos subidos desde el panel (fotos, modelos 3D). Se sirven también
# con DEBUG=False porque SMAV corre con runserver detrás del túnel; con un
# servidor web (Nginx) se puede apagar con DJANGO_SERVE_MEDIA=False.
if settings.DEBUG or settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
