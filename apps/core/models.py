from django.core.validators import FileExtensionValidator
from django.db import models

class CatalogItem(models.Model):
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    price_label = models.CharField(
        max_length=40,
        default="Cotizar",
    )
    badge = models.CharField(max_length=40, blank=True)

    ar_model = models.FileField(
        upload_to="products/ar/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["glb"],
            )
        ],
        verbose_name="Modelo de realidad aumentada",
    )

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Elemento del catálogo"
        verbose_name_plural = "Elementos del catálogo"

    def __str__(self):
        return self.name