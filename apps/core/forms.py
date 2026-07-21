from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


UserModel = get_user_model()


class SMAVUserCreationForm(UserCreationForm):
    """Formulario de creación de usuarios con la identidad visual de SMAV."""

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
        label="Acceso al panel administrativo",
        required=False,
        help_text=(
            "Permite iniciar sesión en las herramientas internas. "
            "No convierte al usuario en superusuario."
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

        self.fields["username"].label = "Nombre de usuario"
        self.fields["username"].help_text = (
            "Máximo 150 caracteres. Puede incluir letras, números y "
            "los símbolos @ . + - _"
        )

        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Confirmar contraseña"

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
                "placeholder": "Escribe una contraseña segura",
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
        email = self.cleaned_data["email"].strip().lower()

        if UserModel.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este correo."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        user.first_name = self.cleaned_data.get(
            "first_name",
            "",
        ).strip()

        user.last_name = self.cleaned_data.get(
            "last_name",
            "",
        ).strip()

        user.email = self.cleaned_data["email"]
        user.is_active = True
        user.is_superuser = False

        if self.can_assign_staff:
            user.is_staff = self.cleaned_data.get(
                "is_staff",
                False,
            )
        else:
            user.is_staff = False

        if commit:
            user.save()

        return user