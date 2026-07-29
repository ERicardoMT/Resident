#!/usr/bin/env bash

set -Eeuo pipefail

trap '
echo
echo "ERROR: El proceso se detuvo en la línea $LINENO."
echo "Revisa el mensaje anterior antes de continuar."
' ERR


echo "=================================================="
echo " CREAR MÓDULO DE SOPORTES ANTIVIBRATORIOS"
echo "=================================================="
echo


# =========================================================
# 1. Verificar ubicación y archivos
# =========================================================

if [[ ! -f "manage.py" ]]; then
    echo "ERROR: No se encontró manage.py."
    echo "Ejecuta este script desde la raíz del proyecto."
    exit 1
fi


required_files=(
    "apps/core/views.py"
    "apps/core/urls.py"
    "templates/core/home.html"
    "templates/vibration/measure.html"
    "templates/stops/stops.html"
    "static/css/style.css"
)


for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: No se encontró $file"
        exit 1
    fi
done


echo "Archivos necesarios encontrados."
echo


# =========================================================
# 2. Crear respaldo temporal
# =========================================================

BACKUP_DIR="/tmp/resident_soportes_antivibratorios_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR/apps/core"
mkdir -p "$BACKUP_DIR/templates/core"
mkdir -p "$BACKUP_DIR/templates/vibration"
mkdir -p "$BACKUP_DIR/templates/stops"
mkdir -p "$BACKUP_DIR/static/css"

cp apps/core/views.py \
    "$BACKUP_DIR/apps/core/views.py"

cp apps/core/urls.py \
    "$BACKUP_DIR/apps/core/urls.py"

cp templates/core/home.html \
    "$BACKUP_DIR/templates/core/home.html"

cp templates/vibration/measure.html \
    "$BACKUP_DIR/templates/vibration/measure.html"

cp templates/stops/stops.html \
    "$BACKUP_DIR/templates/stops/stops.html"

cp static/css/style.css \
    "$BACKUP_DIR/static/css/style.css"


echo "Respaldo creado en:"
echo "$BACKUP_DIR"
echo


# =========================================================
# 3. Modificar vistas, rutas y navegación
# =========================================================

python - <<'PY'
from pathlib import Path
import re


def read(path):
    return Path(path).read_text(
        encoding="utf-8",
    )


def write(path, content):
    Path(path).write_text(
        content,
        encoding="utf-8",
    )


# =========================================================
# apps/core/views.py
# =========================================================

# =========================================================
# apps/core/views.py
# =========================================================

views_path = Path("apps/core/views.py")
views = read(views_path)


new_home = '''def home(request):
    """Muestra el panel principal de SMAV INAHER."""

    menu = [
        {
            "icon": "stops",
            "title": "Soportes antivibratorios",
            "subtitle": (
                "Elige un soporte o mide la vibración "
                "de tu maquinaria"
            ),
            "url_name": "soportes_antivibratorios",
            "available": True,
        },
        {
            "icon": "attenuation",
            "title": "Atenuación y aislamiento",
            "subtitle": (
                "Transmisibilidad según la frecuencia"
            ),
            "url_name": "attenuation",
            "available": True,
        },
        {
            "icon": "catalog",
            "title": "Catálogo de productos",
            "subtitle": (
                "Antivibratorios, niveladores "
                "y componentes"
            ),
            "url_name": "catalogo",
            "available": True,
        },
    ]

    return render(
        request,
        "core/home.html",
        {
            "menu": menu,
        },
    )


def soportes_antivibratorios_view(request):
    """
    Muestra las herramientas relacionadas con soportes
    y medición de vibraciones.
    """

    return render(
        request,
        "core/soportes_antivibratorios.html",
    )
'''


# Localiza home sin depender de cómo esté formateado
# su return render.
home_pattern = re.compile(
    r"^def home\(request\):.*?(?=^@|^def |\Z)",
    re.MULTILINE | re.DOTALL,
)

views, replacements = home_pattern.subn(
    new_home.rstrip() + "\n\n",
    views,
    count=1,
)

if replacements != 1:
    raise SystemExit(
        "ERROR: No fue posible reemplazar "
        "la función home."
    )

write(
    views_path,
    views,
)


# =========================================================
# apps/core/urls.py
# =========================================================

urls_path = Path("apps/core/urls.py")
urls = read(urls_path)

new_route_name = 'name="soportes_antivibratorios"'

if new_route_name not in urls:
    home_route = '''    path(
        "",
        views.home,
        name="home",
    ),
'''

    if home_route not in urls:
        raise SystemExit(
            "ERROR: No se encontró la ruta home."
        )

    support_route = '''
    # Herramientas para soportes antivibratorios
    path(
        "soportes-antivibratorios/",
        views.soportes_antivibratorios_view,
        name="soportes_antivibratorios",
    ),
'''

    urls = urls.replace(
        home_route,
        home_route + support_route,
        1,
    )

write(
    urls_path,
    urls,
)


# =========================================================
# Botón para volver al nuevo módulo
# =========================================================

back_block = '''{% block back %}
<a
  class="icon-btn"
  href="{% url 'soportes_antivibratorios' %}"
  aria-label="Volver a soportes antivibratorios"
>
  <svg
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2.4"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <polyline points="15 18 9 12 15 6"></polyline>
  </svg>
</a>
{% endblock %}


'''

for template_path in (
    Path("templates/vibration/measure.html"),
    Path("templates/stops/stops.html"),
):
    template = read(template_path)

    if "{% block back %}" not in template:
        content_marker = "{% block content %}"

        if content_marker not in template:
            raise SystemExit(
                f"ERROR: No se encontró block content "
                f"en {template_path}"
            )

        template = template.replace(
            content_marker,
            back_block + content_marker,
            1,
        )

        write(
            template_path,
            template,
        )


print(
    "Vistas, rutas y botones modificados."
)
PY


# =========================================================
# 4. Crear plantilla del nuevo módulo
# =========================================================

cat > templates/core/soportes_antivibratorios.html <<'HTML'
{% extends "base.html" %}
{% load static %}

{% block title %}
Soportes antivibratorios | SMAV INAHER
{% endblock %}


{% block content %}
<section class="page support-hub-page">

  <span class="section-kicker">
    Soluciones antivibratorias
  </span>

  <h1 class="page-title">
    Soportes antivibratorios
  </h1>

  <p class="page-lead">
    Reduce la vibración de tu maquinaria o equipo
    industrial. Selecciona la herramienta que necesitas.
  </p>


  <ul class="menu support-hub-menu">

    <!-- Elegir soporte -->
    <li>
      <a
        class="menu-item support-hub-option"
        href="{% url 'stops' %}"
      >
        <span
          class="menu-icon"
          aria-hidden="true"
        >
          <svg
            width="31"
            height="31"
            viewBox="0 0 32 32"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <ellipse
              cx="16"
              cy="24"
              rx="12"
              ry="4"
            ></ellipse>

            <path
              d="M8 23l4-11h8l4 11"
            ></path>

            <ellipse
              cx="16"
              cy="12"
              rx="4"
              ry="2"
              class="icon-accent-fill"
            ></ellipse>
          </svg>
        </span>

        <span class="menu-text">
          <span class="title">
            Elegir mi soporte
          </span>

          <span class="subtitle">
            Ingresa los datos del montaje para evaluar
            la deflexión y dimensionar el soporte.
          </span>
        </span>

        <span
          class="menu-arrow"
          aria-hidden="true"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline
              points="9 18 15 12 9 6"
            ></polyline>
          </svg>
        </span>
      </a>
    </li>


    <!-- Medir vibración -->
    <li>
      <a
        class="menu-item support-hub-option"
        href="{% url 'measure' %}"
      >
        <span
          class="menu-icon"
          aria-hidden="true"
        >
          <svg
            width="31"
            height="31"
            viewBox="0 0 32 32"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M2 16h4l3-8 4 16 3-12 3 8h11"
            ></path>
          </svg>
        </span>

        <span class="menu-text">
          <span class="title">
            Medir vibración
          </span>

          <span class="subtitle">
            Usa el sensor del teléfono para obtener
            frecuencia, RPM, aceleración y espectro FFT.
          </span>
        </span>

        <span
          class="menu-arrow"
          aria-hidden="true"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline
              points="9 18 15 12 9 6"
            ></polyline>
          </svg>
        </span>
      </a>
    </li>

  </ul>


  <div class="note support-hub-note">
    Para medir vibraciones desde un teléfono, permite el
    acceso a los sensores cuando el navegador lo solicite.
  </div>

</section>
{% endblock %}
HTML


# =========================================================
# 5. Agregar estilos específicos
# =========================================================

CSS_MARKER="MÓDULO: SOPORTES ANTIVIBRATORIOS"

if ! grep -q "$CSS_MARKER" static/css/style.css; then
    cat >> static/css/style.css <<'CSS'


/* =========================================================
   MÓDULO: SOPORTES ANTIVIBRATORIOS
   ========================================================= */

.support-hub-page {
  padding-bottom: 34px;
}

.support-hub-menu {
  margin-top: 24px;
}

.support-hub-option {
  min-height: 112px;
  align-items: center;
}

.support-hub-option .menu-icon {
  flex: 0 0 56px;
  width: 56px;
  height: 56px;
}

.support-hub-option .menu-text {
  min-width: 0;
}

.support-hub-option .menu-text .title {
  display: block;
  margin-bottom: 6px;
}

.support-hub-option .menu-text .subtitle {
  display: block;
  line-height: 1.45;
}

.support-hub-note {
  margin-top: 20px;
}


@media (max-width: 480px) {
  .support-hub-option {
    min-height: 104px;
  }

  .support-hub-option .menu-icon {
    flex-basis: 50px;
    width: 50px;
    height: 50px;
  }
}
CSS
fi


# =========================================================
# 6. Comprobar sintaxis
# =========================================================

echo
echo "Comprobando sintaxis..."

python -m py_compile \
    apps/core/views.py \
    apps/core/urls.py


echo "Sintaxis correcta."
echo


# =========================================================
# 7. Comprobar Django y rutas
# =========================================================

python manage.py check

echo
echo "Rutas configuradas:"

python manage.py shell -c "
from django.urls import reverse

print('Nuevo módulo:', reverse('soportes_antivibratorios'))
print('Elegir soporte:', reverse('stops'))
print('Medir vibración:', reverse('measure'))
"


# =========================================================
# 8. Revisar formato
# =========================================================

git diff --check


echo
echo "=================================================="
echo " PROCESO TERMINADO"
echo "=================================================="
echo
echo "Panel principal:"
echo "  Soportes antivibratorios"
echo "  Atenuación y aislamiento"
echo "  Catálogo de productos"
echo
echo "Nuevo módulo:"
echo "  http://127.0.0.1:8000/soportes-antivibratorios/"
echo
echo "Opciones:"
echo "  Elegir mi soporte"
echo "  Medir vibración"
echo
echo "Respaldo temporal:"
echo "  $BACKUP_DIR"
echo
echo "Archivos modificados:"
git status --short