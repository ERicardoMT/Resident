from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.attenuation.urls")),
    path("", include("apps.vibration.urls")),
    path("", include("apps.shock.urls")),
    path("", include("apps.stops.urls")),
    path("", include("apps.datasheet.urls")),
]
