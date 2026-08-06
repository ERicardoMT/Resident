from django.urls import path

from . import views


urlpatterns = [
    path(
        "pies-de-nivelacion/elegir/",
        views.select_leveler,
        name="select_leveler",
    ),
    path(
        "api/niveladores/recomendar/",
        views.recommend_leveler,
        name="recommend_leveler",
    ),
    path(
        "pies-de-nivelacion/verificar/",
        views.leveler,
        name="leveler",
    ),
]