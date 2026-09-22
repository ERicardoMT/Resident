"""Analisis de senales de acelerometro para extraer frecuencia dominante (Hz).

El navegador (movil Android/iOS) captura muestras del acelerometro mediante la
API DeviceMotion y las envia a la API REST. Aqui aplicamos una FFT con numpy
para obtener la frecuencia dominante, la amplitud RMS y el pico de aceleracion.
"""

from __future__ import annotations

import numpy as np


# Constante de gravedad para convertir m/s^2 a g.
G = 9.80665

# Límites defensivos para evitar consumos excesivos
# de memoria y procesamiento.
MIN_INPUT_SAMPLES = 8
MAX_INPUT_SAMPLES = 5000
MAX_DURATION_SECONDS = 10.0
MAX_RESAMPLED_POINTS = 5000

# Frecuencia mínima utilizada para integrar
# aceleración y obtener velocidad vibratoria.
VELOCITY_LOW_CUT_HZ = 1.0


def _uniform_resample(
    times_s: np.ndarray,
    values: np.ndarray,
    fs: float,
):
    """
    Reinterpola las muestras a una malla temporal uniforme.

    DeviceMotion no garantiza un intervalo constante entre
    muestras, por lo que interpolamos linealmente antes
    de ejecutar la FFT.
    """

    t0 = times_s[0]
    t1 = times_s[-1]

    estimated_points = (
        int(
            round(
                (t1 - t0) * fs
            )
        )
        + 1
    )

    n = min(
        max(
            estimated_points,
            2,
        ),
        MAX_RESAMPLED_POINTS,
    )

    uniform_t = np.linspace(
        t0,
        t1,
        n,
    )

    uniform_v = np.interp(
        uniform_t,
        times_s,
        values,
    )

    return uniform_t, uniform_v


def _acceleration_to_velocity(
    acceleration: np.ndarray,
    fs: float,
    low_cut_hz: float = VELOCITY_LOW_CUT_HZ,
) -> np.ndarray:
    """
    Convierte aceleración en m/s² a velocidad en m/s.

    La integración se realiza en el dominio de frecuencia:

        V(f) = A(f) / (j * 2πf)

    Se eliminan las frecuencias muy bajas para evitar
    que pequeños offsets generen una velocidad falsa.
    """

    sample_count = len(
        acceleration
    )

    acceleration_fft = np.fft.rfft(
        acceleration
    )

    frequencies = np.fft.rfftfreq(
        sample_count,
        d=1.0 / fs,
    )

    velocity_fft = np.zeros_like(
        acceleration_fft,
        dtype=np.complex128,
    )

    valid_frequencies = (
        frequencies >= low_cut_hz
    )

    velocity_fft[
        valid_frequencies
    ] = (
        acceleration_fft[
            valid_frequencies
        ]
        / (
            1j
            * 2.0
            * np.pi
            * frequencies[
                valid_frequencies
            ]
        )
    )

    return np.fft.irfft(
        velocity_fft,
        n=sample_count,
    )


def analyze_samples(
    samples: list[dict],
) -> dict:
    """
    Procesa una lista de muestras {t, x, y, z}.

    t:
        Marca de tiempo en milisegundos.

    x, y, z:
        Aceleración en m/s² en cada eje.

    Devuelve frecuencia dominante, RPM,
    aceleración RMS/pico, velocidad vibratoria
    y espectro simplificado.
    """

    # -----------------------------------------------------
    # Validación de cantidad de muestras
    # -----------------------------------------------------

    if (
        not samples
        or len(samples) < MIN_INPUT_SAMPLES
    ):
        raise ValueError(
            (
                "Se necesitan al menos "
                f"{MIN_INPUT_SAMPLES} muestras "
                "para estimar la frecuencia."
            )
        )

    if len(samples) > MAX_INPUT_SAMPLES:
        raise ValueError(
            (
                "No se pueden analizar más de "
                f"{MAX_INPUT_SAMPLES} muestras."
            )
        )

    # -----------------------------------------------------
    # Conversión a arrays NumPy
    # -----------------------------------------------------

    times = np.array(
        [
            float(sample["t"])
            for sample in samples
        ],
        dtype=float,
    )

    x = np.array(
        [
            float(
                sample.get(
                    "x",
                    0.0,
                )
            )
            for sample in samples
        ],
        dtype=float,
    )

    y = np.array(
        [
            float(
                sample.get(
                    "y",
                    0.0,
                )
            )
            for sample in samples
        ],
        dtype=float,
    )

    z = np.array(
        [
            float(
                sample.get(
                    "z",
                    0.0,
                )
            )
            for sample in samples
        ],
        dtype=float,
    )

    # -----------------------------------------------------
    # Validación de valores numéricos
    # -----------------------------------------------------

    if not all(
        np.all(
            np.isfinite(values)
        )
        for values in (
            times,
            x,
            y,
            z,
        )
    ):
        raise ValueError(
            (
                "Las muestras contienen valores "
                "numéricos inválidos."
            )
        )

    # -----------------------------------------------------
    # Orden temporal
    # -----------------------------------------------------

    order = np.argsort(
        times
    )

    times = times[order]
    x = x[order]
    y = y[order]
    z = z[order]

    # Convertimos milisegundos a segundos relativos.
    times_s = (
        times - times[0]
    ) / 1000.0

    duration = float(
        times_s[-1]
        - times_s[0]
    )

    if duration <= 0:
        raise ValueError(
            (
                "La ventana de tiempo es invalida "
                "(duracion menor o igual a cero)."
            )
        )

    if duration > MAX_DURATION_SECONDS:
        raise ValueError(
            (
                "La ventana de tiempo no puede "
                f"superar "
                f"{MAX_DURATION_SECONDS:g} segundos."
            )
        )

    # -----------------------------------------------------
    # DEBUG TEMPORAL
    #
    # Durante la medición en vivo deberían aparecer
    # ventanas cercanas a 3000 ms.
    #
    # Al finalizar deberían aparecer aproximadamente
    # 9700 - 10000 ms.
    #
    # Cuando terminemos de comprobar los 10 segundos,
    # este print se puede eliminar.
    # -----------------------------------------------------

    print(
        "[SMAV DEBUG]",
        "muestras:",
        len(samples),
        "duracion:",
        round(
            duration * 1000.0,
            1,
        ),
        "ms",
    )

    # -----------------------------------------------------
    # Frecuencia de muestreo
    # -----------------------------------------------------

    fs = (
        (len(times_s) - 1)
        / duration
    )

    fs = float(
        np.clip(
            fs,
            1.0,
            400.0,
        )
    )

    # -----------------------------------------------------
    # Reinterpolación independiente de los tres ejes
    # -----------------------------------------------------

    _, x_uniform = _uniform_resample(
        times_s,
        x,
        fs,
    )

    _, y_uniform = _uniform_resample(
        times_s,
        y,
        fs,
    )

    _, z_uniform = _uniform_resample(
        times_s,
        z,
        fs,
    )

    # -----------------------------------------------------
    # Eliminación de componente continua
    #
    # Esto elimina offsets constantes y, cuando se usa
    # accelerationIncludingGravity, elimina la componente
    # estática principal de gravedad.
    # -----------------------------------------------------

    x_dynamic = (
        x_uniform
        - np.mean(
            x_uniform
        )
    )

    y_dynamic = (
        y_uniform
        - np.mean(
            y_uniform
        )
    )

    z_dynamic = (
        z_uniform
        - np.mean(
            z_uniform
        )
    )

    # -----------------------------------------------------
    # Magnitud dinámica de aceleración
    #
    # Esta magnitud se utiliza para RMS y pico.
    #
    # IMPORTANTE:
    # NO se utiliza para calcular la frecuencia dominante.
    # La FFT se realiza por eje más adelante.
    # -----------------------------------------------------

    acceleration_magnitude = np.sqrt(
        x_dynamic**2
        + y_dynamic**2
        + z_dynamic**2
    )

    rms = float(
        np.sqrt(
            np.mean(
                acceleration_magnitude**2
            )
        )
    )

    peak_accel = float(
        np.max(
            acceleration_magnitude
        )
    )

    # -----------------------------------------------------
    # Velocidad vibratoria
    # -----------------------------------------------------

    velocity_x = (
        _acceleration_to_velocity(
            x_dynamic,
            fs,
        )
    )

    velocity_y = (
        _acceleration_to_velocity(
            y_dynamic,
            fs,
        )
    )

    velocity_z = (
        _acceleration_to_velocity(
            z_dynamic,
            fs,
        )
    )

    velocity_magnitude = np.sqrt(
        velocity_x**2
        + velocity_y**2
        + velocity_z**2
    )

    velocity_rms_mms = (
        float(
            np.sqrt(
                np.mean(
                    velocity_magnitude**2
                )
            )
        )
        * 1000.0
    )

    velocity_peak_mms = (
        float(
            np.max(
                velocity_magnitude
            )
        )
        * 1000.0
    )

    # -----------------------------------------------------
    # FFT POR EJE
    #
    # Esta es la corrección importante.
    #
    # Antes se calculaba:
    #
    # sqrt(x² + y² + z²)
    #
    # antes de la FFT, lo que podía convertir una
    # frecuencia f en aproximadamente 2f.
    #
    # Ahora calculamos primero la FFT de X, Y y Z
    # de manera independiente.
    # -----------------------------------------------------

    n = len(
        x_dynamic
    )

    # Ventana Hann para reducir
    # fuga espectral.
    window = np.hanning(
        n
    )

    x_fft = np.fft.rfft(
        x_dynamic
        * window
    )

    y_fft = np.fft.rfft(
        y_dynamic
        * window
    )

    z_fft = np.fft.rfft(
        z_dynamic
        * window
    )

    freqs = np.fft.rfftfreq(
        n,
        d=1.0 / fs,
    )

    # -----------------------------------------------------
    # Energía espectral combinada
    #
    # Combinamos los tres ejes DESPUÉS de ejecutar
    # la FFT.
    # -----------------------------------------------------

    spectral_power = (
        np.abs(
            x_fft
        ) ** 2
        + np.abs(
            y_fft
        ) ** 2
        + np.abs(
            z_fft
        ) ** 2
    )

    # Magnitud combinada utilizada únicamente
    # para dibujar el espectro.
    spectrum = np.sqrt(
        spectral_power
    )

    # -----------------------------------------------------
    # Frecuencia dominante
    # -----------------------------------------------------

    if len(
        spectral_power
    ) > 1:

        search = (
            spectral_power.copy()
        )

        # Ignoramos DC.
        search[0] = 0.0

        peak_index = int(
            np.argmax(
                search
            )
        )

        dominant_hz = float(
            freqs[
                peak_index
            ]
        )

    else:

        dominant_hz = 0.0

    # -----------------------------------------------------
    # Espectro simplificado para el frontend
    # -----------------------------------------------------

    max_points = 64

    if len(freqs) > max_points:

        idx = np.linspace(
            0,
            len(freqs) - 1,
            max_points,
        ).astype(
            int
        )

        spec_freqs = (
            freqs[idx]
        )

        spec_mags = (
            spectrum[idx]
        )

    else:

        spec_freqs = freqs
        spec_mags = spectrum

    max_spectrum_value = float(
        np.max(
            spec_mags
        )
    )

    if max_spectrum_value > 0:
        spec_max = (
            max_spectrum_value
        )
    else:
        spec_max = 1.0

    # -----------------------------------------------------
    # Resultado
    # -----------------------------------------------------

    return {
        "dominant_hz": round(
            dominant_hz,
            2,
        ),

        "rpm": round(
            dominant_hz
            * 60.0,
            1,
        ),

        "sample_rate_hz": round(
            fs,
            1,
        ),

        "sample_count": int(
            n
        ),

        "duration_s": round(
            duration,
            2,
        ),

        "rms_ms2": round(
            rms,
            4,
        ),

        "rms_g": round(
            rms / G,
            5,
        ),

        "peak_ms2": round(
            peak_accel,
            4,
        ),

        "peak_g": round(
            peak_accel / G,
            5,
        ),

        "velocity_rms_mms": round(
            velocity_rms_mms,
            4,
        ),

        "velocity_peak_mms": round(
            velocity_peak_mms,
            4,
        ),

        "spectrum": [
            {
                "hz": round(
                    float(
                        frequency
                    ),
                    2,
                ),
                "amp": round(
                    float(
                        magnitude
                    )
                    / spec_max,
                    4,
                ),
            }
            for frequency, magnitude
            in zip(
                spec_freqs,
                spec_mags,
            )
        ],
    }