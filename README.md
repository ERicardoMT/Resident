# VibraMeter

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
