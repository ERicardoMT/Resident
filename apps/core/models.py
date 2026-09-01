from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse

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
    def external_model_3d_url(self):
        """
        Devuelve el origen remoto del modelo 3D.

        Los modelos importados desde Excel se
        conservan dentro de raw_data para evitar
        duplicar archivos binarios en PostgreSQL.
        """

        technical_sources = (
            "antivibration_data",
            "leveler_data",
        )

        possible_fields = (
            "3D",
            "Modelo 3D",
            "URL 3D",
            "3D URL",
            "Modelo 3D (URL)",
        )

        for relation_name in technical_sources:

            technical_data = getattr(
                self,
                relation_name,
                None,
            )

            if not technical_data:
                continue

            raw_data = (
                technical_data.raw_data
                or {}
            )

            for field_name in possible_fields:

                source_url = str(
                    raw_data.get(
                        field_name,
                        "",
                    )
                    or ""
                ).strip()

                if source_url.startswith(
                    (
                        "https://",
                        "http://",
                    )
                ):
                    return source_url

        return ""


    @property
    def model_url(self):
        """
        URL utilizada por <model-viewer>.

        Prioridad:
        1. Archivo model_3d/ar_model existente.
        2. Proxy Django del modelo remoto.

        El proxy resuelve proveedores externos
        que no permiten CORS en navegador.
        """

        model_file = self.model_file

        if (
            model_file
            and model_file.name
        ):
            try:
                return model_file.url
            except ValueError:
                pass

        if (
            self.pk
            and self.external_model_3d_url
        ):
            return reverse(
                "catalog_model_3d",
                kwargs={
                    "product_id": self.pk,
                },
            )

        return ""


    @property
    def model_file(self):
        """
        Usa primero el modelo agregado con la implementación actual.
        Si un producto antiguo tiene ar_model, también seguirá funcionando.
        """
        return self.model_3d or self.ar_model

    @property
    def catalog_image_url(self):
        """
        Devuelve la mejor imagen disponible para cualquier
        producto del catálogo.

        Prioridad:
        1. Imagen subida manualmente.
        2. Imagen importada del Excel de antivibratorios.
        3. Imagen importada del Excel de niveladores.
        """

        # Imagen subida desde el panel.
        if self.image and self.image.name:
            return self.image.url

        technical_sources = (
            "antivibration_data",
            "leveler_data",
        )

        image_fields = (
            "Imagen",
            "Imagen principal (URL)",
            "Imagen principal",
            "URL de imagen",
            "Imagen URL",
        )

        for relation_name in technical_sources:
            technical_data = getattr(
                self,
                relation_name,
                None,
            )

            if not technical_data:
                continue

            raw_data = (
                technical_data.raw_data
                or {}
            )

            for field_name in image_fields:
                image_url = str(
                    raw_data.get(
                        field_name,
                        "",
                    )
                    or ""
                ).strip()

                if image_url.startswith(
                    (
                        "http://",
                        "https://",
                    )
                ):
                    return image_url

        return ""
    
    @property
    def catalog_technical_sheet_url(self):
        """
        Devuelve la mejor ficha técnica disponible.

        Busca primero un URL técnico explícito
        y después los datos importados del Excel.
        """

        technical_sources = (
            "antivibration_data",
            "leveler_data",
        )

        sheet_fields = (
            "Ficha técnica",
            "Ficha tecnica",
            "URL de ficha",
            "Ficha técnica (URL)",
            "Ficha tecnica (URL)",
            "Ficha",
        )

        for relation_name in technical_sources:
            technical_data = getattr(
                self,
                relation_name,
                None,
            )

            if not technical_data:
                continue

            # Los niveladores tienen product_url
            # como campo propio.
            direct_url = str(
                getattr(
                    technical_data,
                    "product_url",
                    "",
                )
                or ""
            ).strip()

            if direct_url.startswith(
                (
                    "http://",
                    "https://",
                )
            ):
                return direct_url.split()[0]

            raw_data = (
                technical_data.raw_data
                or {}
            )

            for field_name in sheet_fields:
                sheet_url = str(
                    raw_data.get(
                        field_name,
                        "",
                    )
                    or ""
                ).strip()

                if sheet_url.startswith(
                    (
                        "http://",
                        "https://",
                    )
                ):
                    return sheet_url.split()[0]

        return ""

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Elemento del catálogo"
        verbose_name_plural = "Elementos del catálogo"

    def __str__(self):
        return self.name
    
class AntivibrationTechnicalData(models.Model):
    """
    Información técnica de un soporte antivibratorio.

    Los campos utilizados para la recomendación
    provienen de la hoja de cálculo de INAHER.
    """

    product = models.OneToOneField(
        CatalogItem,
        on_delete=models.CASCADE,
        related_name="antivibration_data",
    )

    model_code = models.CharField(
        max_length=160,
        unique=True,
        db_index=True,
    )

    base_diameter = models.CharField(
        max_length=255,
        blank=True,
    )

    base_height = models.CharField(
        max_length=255,
        blank=True,
    )

    screw_diameter = models.CharField(
        max_length=255,
        blank=True,
    )

    screw_height = models.CharField(
        max_length=255,
        blank=True,
    )

    capacity_label = models.CharField(
        max_length=120,
        blank=True,
    )

    capacity_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True,
    )

    elastomer_material = models.TextField(
        blank=True,
    )

    screw_material = models.TextField(
        blank=True,
    )

    source_file = models.CharField(
        max_length=255,
        blank=True,
    )

    source_sheet = models.CharField(
        max_length=255,
        blank=True,
    )

    source_row = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    raw_data = models.JSONField(
        default=dict,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.model_code


class LevelerTechnicalData(models.Model):
    """
    Información técnica de un nivelador.

    Los campos utilizados para la recomendación
    provienen de la hoja de cálculo de INAHER.
    """

    product = models.OneToOneField(
        CatalogItem,
        on_delete=models.CASCADE,
        related_name="leveler_data",
    )

    model_code = models.CharField(
        max_length=160,
        unique=True,
        db_index=True,
    )

    capacity_label = models.CharField(
        max_length=120,
        blank=True,
    )

    capacity_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True,
    )

    type_label = models.CharField(
        max_length=255,
        blank=True,
    )

    metric_threads = models.TextField(
        blank=True,
    )

    standard_threads = models.TextField(
        blank=True,
    )

    base_diameter = models.CharField(
        max_length=255,
        blank=True,
    )

    screw_height = models.CharField(
        max_length=255,
        blank=True,
    )

    screw_material = models.TextField(
        blank=True,
    )

    base_material = models.TextField(
        blank=True,
    )

    product_url = models.URLField(
        max_length=700,
        blank=True,
    )

    source_file = models.CharField(
        max_length=255,
        blank=True,
    )

    source_sheet = models.CharField(
        max_length=255,
        blank=True,
    )

    source_row = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    raw_data = models.JSONField(
        default=dict,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.model_code