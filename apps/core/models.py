from django.db import models

class CatalogItem(models.Model):
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=80, blank=True)
    subcategory = models.CharField(max_length=80, blank=True, null=True)
    description = models.TextField(blank=True)
    price_label = models.CharField(max_length=40, default="Cotizar")
    badge = models.CharField(max_length=40, blank=True)
    
    # --- ESTOS SON LOS CAMPOS QUE EL PULL BORRÓ (Recuperados) ---
    image = models.ImageField(upload_to='productos/', blank=True, null=True)
    model_3d = models.FileField(upload_to='modelos_3d/', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Elemento del catálogo"
        verbose_name_plural = "Elementos del catálogo"

    def __str__(self):
        return self.name