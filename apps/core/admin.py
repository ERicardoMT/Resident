from django.contrib import admin

from .models import CatalogItem


@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price_label",
        "badge",
        "is_active",
        "sort_order",
    )
    list_filter = ("is_active", "category")
    search_fields = ("name", "category", "description")
    ordering = ("sort_order", "name")