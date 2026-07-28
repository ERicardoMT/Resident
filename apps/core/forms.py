from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .models import (
    CatalogCategory,
    CatalogItem,
    CatalogSubcategory,
    SUBCATEGORIES_BY_CATEGORY,
)


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

        category = cleaned_data.get(
            "category"
        )

        subcategory = (
            cleaned_data.get(
                "subcategory"
            )
            or ""
        )

        if not category:
            return cleaned_data

        allowed_subcategories = (
            SUBCATEGORIES_BY_CATEGORY.get(
                category,
                set(),
            )
        )

        if allowed_subcategories:
            if not subcategory:
                self.add_error(
                    "subcategory",
                    (
                        "Selecciona una subcategoría "
                        "para esta categoría."
                    ),
                )
            elif (
                subcategory
                not in allowed_subcategories
            ):
                self.add_error(
                    "subcategory",
                    (
                        "La subcategoría seleccionada "
                        "no pertenece a esta categoría."
                    ),
                )
        elif subcategory:
            cleaned_data["subcategory"] = ""

        return cleaned_data

    def clean_description(self):
        return (
            self.cleaned_data.get(
                "description"
            )
            or ""
        ).strip()

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