from pathlib import Path
import json


from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from .models import (
    CatalogCategory,
    CatalogItem,
    CatalogSubcategory,
    CustomCatalogCategory,
    CustomCatalogSubcategory,
    SUBCATEGORIES_BY_CATEGORY,
)

from .utils import sanitize_catalog_html

UserModel = get_user_model()


class SMAVUserCreationForm(UserCreationForm):
    """Formulario para crear usuarios en el sistema SMAV."""

    first_name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=False,
    )

    last_name = forms.CharField(
        label="Apellidos",
        max_length=150,
        required=False,
    )

    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
    )

    is_staff = forms.BooleanField(
        label="Crear como superusuario",
        required=False,
        help_text=(
            "Otorga acceso completo al sistema, "
            "al panel administrativo y a todos "
            "los permisos."
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = UserModel
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
        )

    def __init__(
        self,
        *args,
        can_assign_staff=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.can_assign_staff = can_assign_staff

        self.fields["username"].label = (
            "Nombre de usuario"
        )

        self.fields["username"].help_text = (
            "Máximo 150 caracteres. Puede incluir "
            "letras, números y los símbolos @ . + - _"
        )

        self.fields["password1"].label = "Contraseña"

        self.fields["password2"].label = (
            "Confirmar contraseña"
        )

        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Ej. nombre.apellido",
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
            }
        )

        self.fields["first_name"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Nombre",
                "autocomplete": "given-name",
            }
        )

        self.fields["last_name"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Apellidos",
                "autocomplete": "family-name",
            }
        )

        self.fields["email"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "usuario@inaher.com",
                "autocomplete": "email",
                "inputmode": "email",
            }
        )

        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": (
                    "Escribe una contraseña segura"
                ),
                "autocomplete": "new-password",
            }
        )

        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Repite la contraseña",
                "autocomplete": "new-password",
            }
        )

        if not can_assign_staff:
            self.fields.pop("is_staff", None)

        self.order_fields(
            [
                "username",
                "first_name",
                "last_name",
                "email",
                "password1",
                "password2",
                "is_staff",
            ]
        )

    def clean_email(self):
        email = (
            self.cleaned_data["email"]
            .strip()
            .lower()
        )

        if UserModel.objects.filter(
            email__iexact=email
        ).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada "
                "con este correo."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        user.first_name = (
            self.cleaned_data.get(
                "first_name",
                "",
            )
            .strip()
        )

        user.last_name = (
            self.cleaned_data.get(
                "last_name",
                "",
            )
            .strip()
        )

        user.email = self.cleaned_data["email"]
        user.is_active = True

        crear_como_superusuario = False

        if self.can_assign_staff:
            crear_como_superusuario = (
                self.cleaned_data.get(
                    "is_staff",
                    False,
                )
            )

        user.is_staff = crear_como_superusuario
        user.is_superuser = crear_como_superusuario

        if commit:
            user.save()

        return user


class CatalogItemForm(forms.ModelForm):
    """Formulario compartido para crear y editar productos."""

    category = forms.ChoiceField(
        label="Categoría",
        choices=CatalogCategory.choices,
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    subcategory = forms.ChoiceField(
        label="Subcategoría",
        required=False,
        choices=[
            (
                "",
                "Selecciona una subcategoría",
            ),
            *CatalogSubcategory.choices,
        ],
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    new_category = forms.CharField(
        label="Nueva categoría",
        max_length=80,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ej. Rodajas industriales",
            }
        ),
    )

    MAX_IMAGE_SIZE = 5 * 1024 * 1024
    MAX_MODEL_SIZE = 20 * 1024 * 1024

    class Meta:
        model = CatalogItem

        fields = (
            "name",
            "category",
            "subcategory",
            "description",
            "price_label",
            "badge",
            "is_active",
            "image",
            "model_3d",
            "ar_model",
        )

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Nombre del producto"
                    ),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "id": "descripcion_editor",
                    "rows": 10,
                    "placeholder": (
                        "Descripción del producto"
                    ),
                }
            ),
            "price_label": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Ejemplo: Cotizar"
                    ),
                }
            ),
            "badge": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: Nuevo",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "product-active-checkbox",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": (
                        ".jpg,.jpeg,.png,.webp"
                    ),
                }
            ),
            "model_3d": (
                forms.ClearableFileInput(
                    attrs={
                        "class": "form-control",
                        "accept": ".glb",
                    }
                )
            ),
            "ar_model": (
                forms.ClearableFileInput(
                    attrs={
                        "class": "form-control",
                        "accept": ".glb",
                    }
                )
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices = list(CatalogCategory.choices)

        known_values = {
            value for value, _ in choices
        }

        custom_categories = (
            CustomCatalogCategory.objects
            .filter(is_active=True)
            .order_by("name")
            .values_list("name", flat=True)
        )

        for name in custom_categories:
            if name not in known_values:
                choices.append((name, name))
                known_values.add(name)

        # Conservar la categoría actual al editar,
        # incluso si fue desactivada.
        if (
            self.instance.pk
            and self.instance.category
            and self.instance.category not in known_values
        ):
            current_category = self.instance.category
            choices.append(
                (current_category, current_category)
            )

        choices.append(
            (
                "__new_category__",
                "+ Agregar nueva categoría",
            )
        )

        self.fields["category"].choices = choices

        subcategory_choices = [
            ("", "Selecciona una subcategoría"),
            *CatalogSubcategory.choices,
        ]

        known_subcategories = {
            value for value, _ in subcategory_choices
        }

        custom_subcategories = (
            CustomCatalogSubcategory.objects
            .filter(
                is_active=True,
                category__in=known_values,
            )
            .order_by("name")
            .values_list("name", flat=True)
        )

        for name in custom_subcategories:
            if name not in known_subcategories:
                subcategory_choices.append(
                    (name, name)
                )
                known_subcategories.add(name)

        # Conservar la subcategoría existente al editar.
        if (
            self.instance.pk
            and self.instance.subcategory
            and self.instance.subcategory not in known_subcategories
        ):
            current_subcategory = self.instance.subcategory
            subcategory_choices.append(
                (current_subcategory, current_subcategory)
            )

        self.fields["subcategory"].choices = (
            subcategory_choices
        )

                # Relación dinámica entre categorías
        # y subcategorías para el frontend.
        subcategories_by_category = {
            str(category): sorted(subcategories)
            for category, subcategories
            in SUBCATEGORIES_BY_CATEGORY.items()
        }

        custom_relations = (
            CustomCatalogSubcategory.objects
            .filter(
                is_active=True,
                category__in=known_values,
            )
            .values_list("category", "name")
        )

        for category, name in custom_relations:
            allowed = (
                subcategories_by_category
                .setdefault(category, [])
            )

            if name not in allowed:
                allowed.append(name)

        # Mantener la selección existente al editar.
        if (
            self.instance.pk
            and self.instance.category
            and self.instance.subcategory
        ):
            allowed = subcategories_by_category.setdefault(
                self.instance.category, []
            )

            if self.instance.subcategory not in allowed:
                allowed.append(self.instance.subcategory)

        self.fields["subcategory"].widget.attrs[
            "data-subcategories-by-category"
        ] = json.dumps(
            subcategories_by_category,
            ensure_ascii=False,
        )

    def clean_name(self):
        name = (
            self.cleaned_data.get("name") or ""
        ).strip()

        if not name:
            raise ValidationError(
                "El nombre del producto es obligatorio."
            )

        return name

    def clean_category(self):
        category = (
            self.cleaned_data.get("category") or ""
        ).strip()

        if not category:
            raise ValidationError(
                "La categoría es obligatoria."
            )

        return category
        

    def clean_subcategory(self):
        return (
            self.cleaned_data.get(
                "subcategory"
            )
            or ""
        ).strip()

    def clean(self):
        cleaned_data = super().clean()

        category = cleaned_data.get("category")
        subcategory = (
            cleaned_data.get("subcategory") or ""
        )

        if not category:
            return cleaned_data
        
        if category == "__new_category__":
            name = (
                cleaned_data.get("new_category") or ""
            ).strip()

            if not name:
                self.add_error(
                    "new_category",
                    "Escribe el nombre de la nueva categoría.",
                )
                return cleaned_data

            internal_names = {
                text.casefold()
                for value, label in CatalogCategory.choices
                for text in (value, label)
            }

            already_exists = (
                CustomCatalogCategory.objects
                .filter(name__iexact=name)
                .exists()
            )

            if (
                name.casefold() in internal_names
                or already_exists
                or name == "__new_category__"
            ):
                self.add_error(
                    "new_category",
                    "Ya existe una categoría con ese nombre "
                    "o el nombre está reservado.",
                )
                return cleaned_data

            cleaned_data["category"] = name
            category = name

        # Subcategorías internas de SMAV.
        internal_allowed = (
            SUBCATEGORIES_BY_CATEGORY.get(
                category,
                set(),
            )
        )

        # Subcategorías personalizadas activas.
        custom_allowed = set(
            CustomCatalogSubcategory.objects
            .filter(
                category=category,
                is_active=True,
            )
            .values_list("name", flat=True)
        )

        allowed_subcategories = (
            set(internal_allowed) | custom_allowed
        )

        # Conservar la subcategoría existente
        # al editar, aunque esté desactivada.
        if (
            self.instance.pk
            and self.instance.category == category
            and self.instance.subcategory
        ):
            allowed_subcategories.add(
                self.instance.subcategory
            )

        if allowed_subcategories and not subcategory:
            self.add_error(
                "subcategory",
                "Selecciona una subcategoría "
                "para esta categoría.",
            )

        elif (
            subcategory
            and subcategory not in allowed_subcategories
        ):
            self.add_error(
                "subcategory",
                "La subcategoría seleccionada "
                "no pertenece a esta categoría.",
            )

        return cleaned_data
    
    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)

        with transaction.atomic():
            if (
                self.data.get("category")
                == "__new_category__"
            ):
                CustomCatalogCategory.objects.get_or_create(
                    name=self.cleaned_data["category"]
                )

            return super().save(commit=True)

    def clean_description(self):
        description = (
            self.cleaned_data.get(
                "description"
            )
            or ""
        ).strip()

        return sanitize_catalog_html(
            description
        )

    def clean_price_label(self):
        return (
            self.cleaned_data.get(
                "price_label"
            )
            or ""
        ).strip()

    def clean_badge(self):
        return (
            self.cleaned_data.get("badge")
            or ""
        ).strip()

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if (
            not image
            or not isinstance(
                image,
                UploadedFile,
            )
        ):
            return image

        extension = (
            Path(image.name)
            .suffix
            .lower()
        )

        allowed_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }

        if extension not in allowed_extensions:
            raise ValidationError(
                "La imagen debe ser JPG, JPEG, "
                "PNG o WEBP."
            )

        if image.size > self.MAX_IMAGE_SIZE:
            raise ValidationError(
                "La imagen no puede superar "
                "los 5 MB."
            )

        return image

    def clean_model_3d(self):
        model = self.cleaned_data.get(
            "model_3d"
        )

        return self._validate_glb(
            model,
            "El modelo 3D",
        )

    def clean_ar_model(self):
        model = self.cleaned_data.get(
            "ar_model"
        )

        return self._validate_glb(
            model,
            "El modelo de realidad aumentada",
        )

    def _validate_glb(
        self,
        model,
        label,
    ):
        if (
            not model
            or not isinstance(
                model,
                UploadedFile,
            )
        ):
            return model

        extension = (
            Path(model.name)
            .suffix
            .lower()
        )

        if extension != ".glb":
            raise ValidationError(
                f"{label} debe estar en formato GLB."
            )

        if model.size > self.MAX_MODEL_SIZE:
            raise ValidationError(
                f"{label} no puede superar los 20 MB."
            )

        return model