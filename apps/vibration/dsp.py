"""Procesamiento digital de señales (DSP) para acelerómetro en SMAV.

Implementa la especificación técnica de la Sección 7 del Libro Maestro:
- 7.1 Remuestreo temporal uniforme basado en la mediana de delta t.
- 7.2 Filtrado pasa-banda Butterworth orden 4 (2 Hz a 0.45*fs).
- 7.2 Espectro Welch con ventana Hann, traslape 50% y zero-padding a 8*fs.
- 7.2 Detección de picos dominantes con find_peaks (prominencia >= 4x mediana).
- 7.3 Resolución de alias con RPM de placa de motor.
- 7.4 Semáforo por aceleración RMS y detección de impactos (factor de cresta > 4).
- 7.5 Cruce con la frecuencia por micrófono (apps.vibration.acoustic).
- 7.6 Respuesta estandarizada del endpoint /api/analyze/.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np
import scipy.signal

from .acoustic import analyze_audio, match_accelerometer

# Límites defensivos
MIN_SAMPLES = 8
MAX_SAMPLES = 10000
MIN_DURATION_S = 0.5
MAX_DURATION_S = 15.0

# Umbrales del semáforo INAHER (Sección 7.4)
RMS_LEVEL_LOW_MAX = 0.5
RMS_LEVEL_MEDIUM_MAX = 2.0

# 7.3: para confirmar la placa el pico debe tener al menos esta fracción de la
# potencia del pico dominante (-10 dB). Descarta lóbulos laterales de la ventana
# Hann, que en señales limpias pasan el criterio de 4x la mediana.
PLACA_MIN_REL_POWER = 0.10


def _parabolic_interpolation(
    freqs: np.ndarray,
    psd: np.ndarray,
    peak_idx: int,
) -> float:
    """Afina la frecuencia de un pico usando interpolación parabólica (±0.05 Hz)."""
    if 0 < peak_idx < len(psd) - 1:
        alpha = float(psd[peak_idx - 1])
        beta = float(psd[peak_idx])
        gamma = float(psd[peak_idx + 1])
        denom = alpha - 2.0 * beta + gamma
        if abs(denom) > 1e-12:
            delta = 0.5 * (alpha - gamma) / denom
            df = float(freqs[1] - freqs[0])
            return float(freqs[peak_idx] + delta * df)
    return float(freqs[peak_idx])


def process_vibration_samples(
    samples: Sequence[dict[str, Any]],
    rpm_placa: float | int | None = None,
    gravity_included: bool = False,
    user_agent: str = "",
    audio_pcm16: str | None = None,
    audio_sample_rate: int | None = None,
) -> dict[str, Any]:
    """Procesa una serie temporal de muestras del acelerómetro y devuelve métricas completas."""
    if not samples or len(samples) < MIN_SAMPLES:
        raise ValueError(
            f"Se necesitan al menos {MIN_SAMPLES} muestras para el análisis."
        )

    if len(samples) > MAX_SAMPLES:
        raise ValueError(
            f"No se pueden procesar más de {MAX_SAMPLES} muestras."
        )

    # 1. Extracción y validación numérica
    raw_times = np.array([float(s["t"]) for s in samples], dtype=float)
    raw_x = np.array([float(s.get("x", 0.0)) for s in samples], dtype=float)
    raw_y = np.array([float(s.get("y", 0.0)) for s in samples], dtype=float)
    raw_z = np.array([float(s.get("z", 0.0)) for s in samples], dtype=float)

    if not all(
        np.all(np.isfinite(arr))
        for arr in (raw_times, raw_x, raw_y, raw_z)
    ):
        raise ValueError("Las muestras contienen valores numéricos inválidos.")

    # Orden temporal estricto
    order = np.argsort(raw_times)
    times = raw_times[order]
    x = raw_x[order]
    y = raw_y[order]
    z = raw_z[order]

    # Tiempo en segundos relativos
    times_s = (times - times[0]) / 1000.0
    duration_s = float(times_s[-1] - times_s[0])

    if duration_s <= 0:
        raise ValueError("La duración de la muestra debe ser mayor a cero.")

    # 7.2.1: fs = mediana de 1/delta t
    dt = np.diff(times_s)
    valid_dt = dt[dt > 0]
    if len(valid_dt) == 0:
        raise ValueError("Intervalos de tiempo inválidos entre muestras.")

    fs = float(np.median(1.0 / valid_dt))
    # Limitar fs a rango operacional razonable
    fs = float(np.clip(fs, 10.0, 250.0))

    # Malla temporal uniforme
    num_uniform_points = int(round(duration_s * fs)) + 1
    t_uniform = np.linspace(times_s[0], times_s[-1], num_uniform_points)
    x_u = np.interp(t_uniform, times_s, x)
    y_u = np.interp(t_uniform, times_s, y)
    z_u = np.interp(t_uniform, times_s, z)

    # 7.2.2: Quitar media de cada eje
    x_d = x_u - np.mean(x_u)
    y_d = y_u - np.mean(y_u)
    z_d = z_u - np.mean(z_u)

    # 7.2.4: Banda de análisis Butterworth orden 4 (2 Hz a 0.45*fs)
    f_low = 2.0
    f_high = 0.45 * fs

    if f_high > f_low and len(x_d) > 15:
        b, a = scipy.signal.butter(4, [f_low, f_high], btype="bandpass", fs=fs)
        x_filt = scipy.signal.filtfilt(b, a, x_d)
        y_filt = scipy.signal.filtfilt(b, a, y_d)
        z_filt = scipy.signal.filtfilt(b, a, z_d)

        # Amplitud: solo pasa-altos de 2 Hz. El tope de 0.45*fs es para el
        # espectro; aplicado aquí borraría la vibración entre 27 y 30 Hz
        # (taladro a 1,720 rpm) y el semáforo diría "Baja" (decisión 4).
        b_hp, a_hp = scipy.signal.butter(4, f_low, btype="highpass", fs=fs)
        x_amp = scipy.signal.filtfilt(b_hp, a_hp, x_d)
        y_amp = scipy.signal.filtfilt(b_hp, a_hp, y_d)
        z_amp = scipy.signal.filtfilt(b_hp, a_hp, z_d)
    else:
        x_filt, y_filt, z_filt = x_d, y_d, z_d
        x_amp, y_amp, z_amp = x_d, y_d, z_d

    # Margen para descartar transitorios de inicio/fin del filtro IIR (0.5 s)
    transient_margin = min(int(round(0.5 * fs)), len(x_filt) // 4)
    if len(x_filt) > 2 * transient_margin:
        valid_slice = slice(transient_margin, -transient_margin)
    else:
        valid_slice = slice(None)

    # 7.2.5: RMS y pico sobre la señal filtrada (pasa-altos 2 Hz) en 3D
    mag_amp = np.sqrt(x_amp**2 + y_amp**2 + z_amp**2)
    mag_eval = mag_amp[valid_slice]

    rms_ms2 = float(np.sqrt(np.mean(mag_eval**2)))
    peak_ms2 = float(np.max(mag_eval)) if len(mag_eval) > 0 else 0.0

    # 7.2.10: Factor de cresta y detección de golpes
    crest = float(peak_ms2 / rms_ms2) if rms_ms2 > 1e-6 else 0.0
    impacts = bool(crest > 4.0)

    # 7.4: Semáforo
    if rms_ms2 < RMS_LEVEL_LOW_MAX:
        level = "low"
    elif rms_ms2 <= RMS_LEVEL_MEDIUM_MAX:
        level = "medium"
    else:
        level = "high"

    # 7.2.3: Para el espectro usar el eje de mayor varianza
    variances = [
        float(np.var(x_filt[valid_slice])),
        float(np.var(y_filt[valid_slice])),
        float(np.var(z_filt[valid_slice])),
    ]
    axes_filt = [x_filt, y_filt, z_filt]
    spectral_signal = axes_filt[int(np.argmax(variances))]

    # 7.2.6: Espectro con Welch (Hann, 4 s, traslape 50%, zero-padding 8*fs)
    nperseg = min(len(spectral_signal), int(round(4.0 * fs)))
    if nperseg < 8:
        nperseg = len(spectral_signal)
    noverlap = nperseg // 2
    nfft = max(nperseg, int(round(8.0 * fs)))

    freqs, psd = scipy.signal.welch(
        spectral_signal,
        fs=fs,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        nfft=nfft,
        scaling="spectrum",
    )

    # 7.2.7: Búsqueda de picos dominantes en banda 2 Hz a 0.45*fs
    band_mask = (freqs >= f_low) & (freqs <= f_high)
    df = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 1.0
    min_distance = max(1, int(round(1.0 / df)))

    detected_peaks: list[int] = []
    if np.any(band_mask):
        median_psd = float(np.median(psd[band_mask]))
        prominence = 4.0 * median_psd
        raw_peaks, _ = scipy.signal.find_peaks(
            psd,
            prominence=prominence,
            distance=min_distance,
        )
        detected_peaks = [p for p in raw_peaks if f_low <= freqs[p] <= f_high]

    dominant_hz: float | None = None
    frequency_status = "unclear"
    frequency_message = "No se detectó una frecuencia clara."
    frequency_note: str | None = None

    if detected_peaks:
        # Pico con mayor potencia espectral
        best_peak = max(detected_peaks, key=lambda p: psd[p])
        f_refined = _parabolic_interpolation(freqs, psd, best_peak)

        # 7.2.8: Cerca del límite (0.40*fs < f <= 0.45*fs)
        if 0.40 * fs < f_refined <= 0.45 * fs:
            dominant_hz = round(f_refined, 1)
            frequency_status = "near_limit"
            frequency_message = "Cerca del límite del celular."
        elif f_refined <= 0.40 * fs:
            dominant_hz = round(f_refined, 1)
            frequency_status = "clear"
            frequency_message = "Frecuencia clara."

            # Nota para f > 0.30*fs si no hay placa
            if f_refined > 0.30 * fs and not rpm_placa:
                reflejo_teorico = abs(f_refined - fs)
                frequency_note = (
                    f"Podría ser reflejo de {reflejo_teorico:.1f} Hz; "
                    "captura las rpm de placa para confirmar."
                )

    # Picos fuertes del acelerómetro (descarta lóbulos de la ventana Hann)
    max_peak_power = max((psd[p] for p in detected_peaks), default=0.0)
    strong_peaks = [
        p for p in detected_peaks
        if psd[p] >= PLACA_MIN_REL_POWER * max_peak_power
    ]

    # 7.5: Frecuencia por micrófono y cruce con el acelerómetro.
    # El micrófono solo aporta frecuencia; la amplitud no cambia.
    acoustic_hz: float | None = None
    acoustic_confidence: str | None = None
    acoustic_harmonics = 0
    if audio_pcm16 and audio_sample_rate:
        acoustic = analyze_audio(audio_pcm16, int(audio_sample_rate))
        f0 = acoustic["acoustic_hz"]
        acoustic_harmonics = acoustic["acoustic_harmonics"]

        if f0 is not None:
            acoustic_hz = round(f0, 1)
            accel_peaks_hz = [
                _parabolic_interpolation(freqs, psd, p) for p in strong_peaks
            ]
            matched_hz = match_accelerometer(f0, accel_peaks_hz, fs)

            if matched_hz is not None:
                acoustic_confidence = "high"
                dominant_hz = round(f0, 1)
                frequency_note = None
                if f0 > 0.45 * fs:
                    frequency_status = "aliased_confirmed"
                    frequency_message = (
                        f"{f0:.1f} Hz ≈ {int(round(f0 * 60))} rpm. "
                        f"El celular lo ve reflejado en {matched_hz:.1f} Hz "
                        "por su límite de muestreo; el sonido de la máquina lo confirma."
                    )
                else:
                    frequency_status = "confirmed"
                    frequency_message = "Coincide con el sonido de la máquina."
            else:
                acoustic_confidence = "low"
                movement_text = (
                    f"el movimiento {dominant_hz:.1f} Hz"
                    if dominant_hz is not None
                    else "el movimiento no muestra una frecuencia clara"
                )
                frequency_note = (
                    f"Dos lecturas distintas: el sonido marca {f0:.1f} Hz "
                    f"y {movement_text}."
                )

    # 7.3: Verificación y resolución de alias con RPM de placa
    if rpm_placa and float(rpm_placa) > 0:
        rpm_val = float(rpm_placa)
        fn = rpm_val / 60.0

        # Candidatos esperados por réplica/alias en muestreo discreto
        candidates = [fn, abs(fn - fs), abs(fn - 2.0 * fs), fn + fs]
        # Filtrar candidatos que caen dentro del ancho de banda medible del sensor
        valid_candidates = [
            c for c in candidates if 2.0 <= c <= 0.50 * fs
        ]

        matched_candidate: float | None = None
        matched_peak_hz: float | None = None

        # Solo cuentan picos que pasaron el criterio de prominencia (7.2.7).
        # Buscar el máximo local en ±5 % sin ese criterio confirma la placa
        # con fuga espectral aunque la máquina gire a otra velocidad.
        for c in valid_candidates:
            for p in strong_peaks:
                peak_f = _parabolic_interpolation(freqs, psd, p)
                if abs(peak_f - c) / c <= 0.05:
                    matched_candidate = c
                    matched_peak_hz = peak_f
                    break
            if matched_candidate is not None:
                break

        if matched_candidate is not None and matched_peak_hz is not None:
            # Caso 1: Coincide con candidato plegado (alias)
            if abs(matched_candidate - fn) / fn > 0.05:
                dominant_hz = round(fn, 1)
                frequency_status = "aliased_confirmed"
                frequency_message = (
                    f"{fn:.1f} Hz ≈ {int(round(rpm_val))} rpm. "
                    f"El celular lo ve reflejado en {matched_peak_hz:.1f} Hz "
                    "por su límite de muestreo; coincide con la placa."
                )
            # Caso 2: Coincide directamente dentro de rango
            else:
                dominant_hz = round(matched_peak_hz, 1)
                frequency_status = "confirmed"
                frequency_message = "Coincide con la placa."
        else:
            # La frecuencia no se confirma: no se pasa al selector (decisión 2)
            dominant_hz = None
            frequency_note = None
            frequency_status = "not_found"
            frequency_message = (
                "No se detectó la frecuencia de placa. "
                "Revisa que el celular esté bien apoyado."
            )

    dominant_rpm = (
        int(round(dominant_hz * 60.0))
        if dominant_hz is not None
        else None
    )

    # Espectro simplificado (64 puntos) para renderizado ligero en cliente
    spectrum_max_points = 64
    nyquist_mask = (freqs >= 0.0) & (freqs <= 0.5 * fs)
    freqs_sub = freqs[nyquist_mask]
    psd_sub = psd[nyquist_mask]

    if len(freqs_sub) > spectrum_max_points:
        sub_indices = np.linspace(
            0,
            len(freqs_sub) - 1,
            spectrum_max_points,
            dtype=int,
        )
        spec_freqs = freqs_sub[sub_indices]
        spec_mags = psd_sub[sub_indices]
    else:
        spec_freqs = freqs_sub
        spec_mags = psd_sub

    max_val = float(np.max(spec_mags)) if len(spec_mags) > 0 else 1.0
    norm_val = max_val if max_val > 0 else 1.0

    spectrum_points = [
        {
            "hz": round(float(f), 2),
            "amp": round(float(m) / norm_val, 4),
        }
        for f, m in zip(spec_freqs, spec_mags)
    ]

    # Respuesta conforme a Sección 7.6
    # Incluye campos de compatibilidad para el modelo de base de datos VibrationMeasurement
    G_CONST = 9.80665
    rms_g = round(rms_ms2 / G_CONST, 4)
    peak_g = round(peak_ms2 / G_CONST, 4)

    return {
        "sample_rate_hz": round(fs, 1),
        "sample_count": int(len(t_uniform)),
        "duration_s": round(duration_s, 2),
        "rms_ms2": round(rms_ms2, 2),
        "rms_g": rms_g,
        "peak_ms2": round(peak_ms2, 2),
        "peak_g": peak_g,
        "crest": round(crest, 2),
        "impacts": impacts,
        "level": level,
        "dominant_hz": dominant_hz,
        "dominant_rpm": dominant_rpm,
        "rpm": dominant_rpm if dominant_rpm is not None else 0.0,
        "frequency_status": frequency_status,
        "frequency_message": frequency_message,
        "frequency_note": frequency_note,
        "f_min_hz": round(f_low, 1),
        "f_max_hz": round(f_high, 1),
        "rpm_placa": float(rpm_placa) if rpm_placa else None,
        "gravity_included": gravity_included,
        "acoustic_hz": acoustic_hz,
        "acoustic_rpm": (
            int(round(acoustic_hz * 60.0))
            if acoustic_hz is not None
            else None
        ),
        "acoustic_confidence": acoustic_confidence,
        "acoustic_harmonics": acoustic_harmonics,
        "acoustic_used": bool(audio_pcm16 and audio_sample_rate),
        "velocity_rms_mms": 0.0,
        "velocity_peak_mms": 0.0,
        "spectrum": spectrum_points,
    }
