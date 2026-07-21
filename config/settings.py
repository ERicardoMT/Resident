"""Configuración de Django para el proyecto SMAV INAHER."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Clave solo para desarrollo. Cambiar en produccion.
SECRET_KEY = "django-insecure-dev-vibrameter-change-me-in-production"

DEBUG = True

# Permitimos cualquier host porque el preview se sirve tras un proxy.
ALLOWED_HOSTS = ["*"]

# Confiamos en cualquier origen https para CSRF dentro del preview.
CSRF_TRUSTED_ORIGINS = [
    "https://*.vercel.run",
    "https://*.vusercontent.net",
    "https://*.v0.dev",
    "https://*.v0.app",
]

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
    # Local
    "apps.core",
    "apps.attenuation",
    "apps.vibration",
    "apps.shock",
    "apps.stops",
    "apps.leveler",
]

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

# El preview embebe la app en un iframe.
X_FRAME_OPTIONS = "ALLOWALL"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS abierto: la app movil / navegador puede llamar a la API libremente.
CORS_ALLOW_ALL_ORIGINS = True

# DRF sin autenticacion por ahora (medicion en tiempo real, sin persistencia).
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}
