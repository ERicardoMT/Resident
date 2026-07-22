from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.conf import settings  # <-- Agregado para leer el settings.py
from django.conf.urls.static import static  # <-- Agregado para servir archivos estáticos/media


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.attenuation.urls")),
    path("", include("apps.vibration.urls")),
    path("", include("apps.shock.urls")),
    path("", include("apps.stops.urls")),
    path("", include("apps.leveler.urls")),
]



if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )