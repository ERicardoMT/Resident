"""Analisis de senales de acelerometro para extraer frecuencia dominante (Hz).

El navegador (movil Android/iOS) captura muestras del acelerometro mediante la
API DeviceMotion y las envia a la API REST. Aqui aplicamos una FFT con numpy
para obtener la frecuencia dominante, la amplitud RMS y el pico de aceleracion.
"""
from __future__ import annotations

import numpy as np

# Constante de gravedad para convertir m/s^2 a g.
G = 9.80665


def _uniform_resample(times_s: np.ndarray, values: np.ndarray, fs: float):
    """Reinterpola las muestras a una malla temporal uniforme.

    DeviceMotion no garantiza un intervalo constante entre muestras, por lo que
    interpolamos linealmente sobre una malla uniforme antes de la FFT.
    """
    t0, t1 = times_s[0], times_s[-1]
    n = max(int(round((t1 - t0) * fs)) + 1, 2)
    uniform_t = np.linspace(t0, t1, n)
    uniform_v = np.interp(uniform_t, times_s, values)
    return uniform_t, uniform_v


def analyze_samples(samples: list[dict]) -> dict:
    """Procesa una lista de muestras {t, x, y, z} y devuelve metricas.

    - t: marca de tiempo en milisegundos
    - x, y, z: aceleracion en m/s^2 en cada eje

    Devuelve un diccionario con la frecuencia dominante y estadisticas asociadas.
    """
    if not samples or len(samples) < 8:
        raise ValueError(
            "Se necesitan al menos 8 muestras para estimar la frecuencia."
        )

    times = np.array([float(s["t"]) for s in samples], dtype=float)
    x = np.array([float(s.get("x", 0.0)) for s in samples], dtype=float)
    y = np.array([float(s.get("y", 0.0)) for s in samples], dtype=float)
    z = np.array([float(s.get("z", 0.0)) for s in samples], dtype=float)

    # Ordenamos por tiempo por seguridad y pasamos a segundos relativos.
    order = np.argsort(times)
    times, x, y, z = times[order], x[order], y[order], z[order]
    times_s = (times - times[0]) / 1000.0

    duration = float(times_s[-1] - times_s[0])
    if duration <= 0:
        raise ValueError("La ventana de tiempo es invalida (duracion <= 0).")

    # Magnitud del vector de aceleracion (independiente de la orientacion).
    magnitude = np.sqrt(x**2 + y**2 + z**2)

    # Frecuencia de muestreo media a partir de las marcas de tiempo.
    fs = (len(times_s) - 1) / duration
    fs = float(np.clip(fs, 1.0, 400.0))

    # Reinterpolamos a malla uniforme.
    _, mag_uniform = _uniform_resample(times_s, magnitude, fs)

    # Quitamos la componente continua (gravedad / offset) restando la media.
    signal = mag_uniform - np.mean(mag_uniform)

    n = len(signal)
    # Ventana de Hann para reducir la fuga espectral.
    window = np.hanning(n)
    windowed = signal * window

    # FFT real y eje de frecuencias.
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)

    # Ignoramos el bin DC (0 Hz) al buscar el pico.
    if len(spectrum) > 1:
        search = spectrum.copy()
        search[0] = 0.0
        peak_index = int(np.argmax(search))
        dominant_hz = float(freqs[peak_index])
    else:
        dominant_hz = 0.0

    rms = float(np.sqrt(np.mean(signal**2)))
    peak_accel = float(np.max(np.abs(signal)))

    # Espectro simplificado para graficar en el cliente (hasta 64 puntos).
    max_points = 64
    if len(freqs) > max_points:
        idx = np.linspace(0, len(freqs) - 1, max_points).astype(int)
        spec_freqs = freqs[idx]
        spec_mags = spectrum[idx]
    else:
        spec_freqs = freqs
        spec_mags = spectrum

    spec_max = float(np.max(spec_mags)) if np.max(spec_mags) > 0 else 1.0

    return {
        "dominant_hz": round(dominant_hz, 2),
        "rpm": round(dominant_hz * 60.0, 1),
        "sample_rate_hz": round(fs, 1),
        "sample_count": int(n),
        "duration_s": round(duration, 2),
        "rms_ms2": round(rms, 4),
        "rms_g": round(rms / G, 5),
        "peak_ms2": round(peak_accel, 4),
        "peak_g": round(peak_accel / G, 5),
        "spectrum": [
            {"hz": round(float(f), 2), "amp": round(float(m) / spec_max, 4)}
            for f, m in zip(spec_freqs, spec_mags)
        ],
    }
