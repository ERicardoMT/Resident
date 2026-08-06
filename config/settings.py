"""Configuración de Django para el proyecto SMAV INAHER."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# Carga las variables del archivo .env sin reemplazar
# variables que ya existan en el sistema operativo.
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    """
    Convierte una variable de entorno en booleano.
    """

    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "si",
        "sí",
    }


def env_list(name, default=""):
    """
    Convierte una variable separada por comas en lista.
    """

    value = os.getenv(name, default)

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def required_env(name):
    """
    Obtiene una variable obligatoria o detiene Django
    mostrando un mensaje entendible.
    """

    value = os.getenv(name)

    if not value:
        raise ImproperlyConfigured(
            f'Falta la variable de entorno obligatoria "{name}". '
            "Revisa el archivo .env."
        )

    return value


# =========================================================
# Seguridad y entorno
# =========================================================

SECRET_KEY = required_env(
    "DJANGO_SECRET_KEY"
)

DEBUG = env_bool(
    "DJANGO_DEBUG",
    default=False,
)

ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
)


# =========================================================
# Aplicaciones
# =========================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Terceros
    "rest_framework",
    "corsheaders",

    # Locales
    "apps.core",
    "apps.attenuation",
    "apps.vibration",
    "apps.stops",
    "apps.leveler",
]


# =========================================================
# Middleware
# =========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# El proyecto todavía utiliza previews dentro de iframe.
# Esta configuración se puede endurecer antes de producción.
X_FRAME_OPTIONS = "ALLOWALL"


# =========================================================
# URLs y templates
# =========================================================

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django."
            "DjangoTemplates"
        ),
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors."
                    "request"
                ),
                (
                    "django.contrib.auth."
                    "context_processors.auth"
                ),
                (
                    "django.contrib.messages."
                    "context_processors.messages"
                ),
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# =========================================================
# Base de datos PostgreSQL
# =========================================================

DATABASES = {
    "default": {
        "ENGINE": (
            "django.db.backends.postgresql"
        ),
        "NAME": required_env(
            "POSTGRES_DB"
        ),
        "USER": required_env(
            "POSTGRES_USER"
        ),
        "PASSWORD": required_env(
            "POSTGRES_PASSWORD"
        ),
        "HOST": os.getenv(
            "POSTGRES_HOST",
            "127.0.0.1",
        ),
        "PORT": os.getenv(
            "POSTGRES_PORT",
            "5432",
        ),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}


# =========================================================
# Validación de contraseñas
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# =========================================================
# Idioma y zona horaria
# =========================================================

LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"

USE_I18N = True
USE_TZ = True


# =========================================================
# Archivos estáticos y archivos subidos
# =========================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# =========================================================
# Autenticación
# =========================================================

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"


DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)


# =========================================================
# CORS
# =========================================================

CORS_ALLOW_ALL_ORIGINS = env_bool(
    "CORS_ALLOW_ALL_ORIGINS",
    default=DEBUG,
)

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
)


# =========================================================
# Django REST Framework
# =========================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        (
            "rest_framework.throttling."
            "AnonRateThrottle"
        ),
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        (
            "rest_framework.renderers."
            "BrowsableAPIRenderer"
        ),
    ],
}