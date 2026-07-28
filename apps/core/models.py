from django.core.validators import FileExtensionValidator
from django.db import models

class CatalogCategory(models.TextChoices):
    ANTIVIBRATORIOS = (
        "antivibratorios",
        "Antivibratorios",
    )

    PATAS_NIVELADORAS = (
        "patas_niveladoras",
        "Patas niveladoras",
    )

    ACCIONAMIENTO = (
        "accionamiento",
        "Elementos de accionamiento y maniobra",
    )

    MOBILIARIO = (
        "mobiliario",
        "Niveladores para mobiliario",
    )


class CatalogSubcategory(models.TextChoices):
    COLGANTES = (
        "colgantes",
        "Colgantes antivibración",
    )

    NIVELADORES_MAQUINARIA = (
        "niveladores_maq",
        "Niveladores antivibración para maquinaria",
    )

    PIES = (
        "pies",
        "Pies antivibración",
    )

    SOPORTES_PISO = (
        "soportes_piso",
        "Soportes antivibración con anclaje al piso",
    )

    TACONES = (
        "tacones",
        "Tacones antivibración",
    )

    ALTA_RESISTENCIA = (
        "alta_resistencia",
        "Alta resistencia",
    )

    ANCLAJE_PISO = (
        "anclaje_piso",
        "Anclaje al piso",
    )

    ANTIDERRAPANTE = (
        "antiderrapante",
        "Antiderrapante",
    )

    ANTIVIBRACION = (
        "antivibracion",
        "Antivibración",
    )

    CON_ROTULA = (
        "con_rotula",
        "Con rótula",
    )

    USO_RUDO = (
        "uso_rudo",
        "Uso rudo",
    )


SUBCATEGORIES_BY_CATEGORY = {
    CatalogCategory.ANTIVIBRATORIOS: {
        CatalogSubcategory.COLGANTES,
        CatalogSubcategory.NIVELADORES_MAQUINARIA,
        CatalogSubcategory.PIES,
        CatalogSubcategory.SOPORTES_PISO,
        CatalogSubcategory.TACONES,
    },
    CatalogCategory.PATAS_NIVELADORAS: {
        CatalogSubcategory.ALTA_RESISTENCIA,
        CatalogSubcategory.ANCLAJE_PISO,
        CatalogSubcategory.ANTIDERRAPANTE,
        CatalogSubcategory.ANTIVIBRACION,
        CatalogSubcategory.CON_ROTULA,
        CatalogSubcategory.USO_RUDO,
    },
    CatalogCategory.ACCIONAMIENTO: set(),
    CatalogCategory.MOBILIARIO: set(),
}

class CatalogItem(models.Model):
    name = models.CharField(max_length=160)
    category = models.CharField(
    max_length=80,
    choices=CatalogCategory.choices,
    )
    subcategory = models.CharField(
    max_length=80,
    choices=CatalogSubcategory.choices,
    blank=True,
    null=True,
    )
    description = models.TextField(blank=True)
    price_label = models.CharField(
        max_length=40,
        default="Cotizar",
    )
    badge = models.CharField(max_length=40, blank=True)

    # Campos agregados por Víctor: se conservan.
    image = models.ImageField(
        upload_to="productos/",
        blank=True,
        null=True,
    )

    model_3d = models.FileField(
        upload_to="modelos_3d/",
        blank=True,
        null=True,
    )

    # Campo de la implementación anterior de RA.
    # Su migración ya existe, por eso debe volver al modelo.
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

    @property
    def model_file(self):
        """
        Usa primero el modelo agregado con la implementación actual.
        Si un producto antiguo tiene ar_model, también seguirá funcionando.
        """
        return self.model_3d or self.ar_model

    @property
    def model_url(self):
        model_file = self.model_file

        if not model_file:
            return ""

        return model_file.url

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Elemento del catálogo"
        verbose_name_plural = "Elementos del catálogo"

    def __str__(self):
        return self.name