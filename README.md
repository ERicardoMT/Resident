# SMAV INAHER

Sistema de Medición y Análisis Vibratorio de INAHER.

## Arquitectura actual

```text
config/           # Configuracion global de Django
apps/
  core/           # Home y menu principal
  vibration/      # Medicion vibratoria, API y FFT
  attenuation/    # Atenuacion vibratoria
  shock/          # Respuesta a choque
  stops/          # Calculo de topes
  datasheet/      # Hojas de datos
templates/
static/
manage.py
requirements.txt
db.sqlite3
```

## Reglas de la estructura

- Cada modulo funcional vive en su propia app.
- Cada app tiene su `views.py`, `urls.py` y sus templates propios.
- La logica de calculo no se mezcla con las plantillas.
- `config/` solo contiene configuracion global.

## Flujo principal

1. `config/urls.py` enruta hacia las apps.
2. `apps/core/` muestra el menu principal.
3. `apps/vibration/` recibe muestras, analiza la señal y devuelve Hz/RPM.
4. `apps/attenuation/`, `apps/shock/`, `apps/stops/` y `apps/datasheet/` resuelven cada calculo o vista.

## Inicio rapido

En PowerShell, desde la raiz del proyecto:

```powershell
# Crear el entorno virtual, solo la primera vez
py -m venv venv

# Activar el entorno virtual
.\venv\Scripts\Activate.ps1
source venv/Scripts/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar migraciones si hace falta
python manage.py migrate

# Levantar el servidor local
python manage.py runserver
```

Luego abre `http://127.0.0.1:8000/` en el navegador.

Si PowerShell bloquea la activacion del entorno, usa esta orden una sola vez en la misma ventana:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
