"""Frecuencia de giro por micrófono (Sección 7.5 del Libro Maestro).

Base: Paramo-Balsa et al., Sensors 2021 (PMC8271583). El celular apoyado en el
chasis capta el sonido estructural de la máquina; la frecuencia de giro se
identifica por sus armónicos. El micrófono solo aporta frecuencia: la amplitud
(RMS, pico) siempre sale del acelerómetro.
"""

from __future__ import annotations

import base64
import binascii

import numpy as np
import scipy.signal

# Banda de búsqueda y resolución (nfft = 2^20 -> ~0.05 Hz a 48 kHz)
ACOUSTIC_F_MIN_HZ = 10.0
ACOUSTIC_F_MAX_HZ = 700.0
ACOUSTIC_NFFT = 2 ** 20
ACOUSTIC_TOP_PEAKS = 11

# Hipótesis armónica: k = 1..11 dentro de ±1 %, mínimo 3 armónicos
HARMONIC_MAX_K = 11
HARMONIC_TOLERANCE = 0.01
HARMONIC_MIN_COUNT = 3

# Red eléctrica: 60 Hz y sus múltiplos (±0.5 Hz) no cuentan como armónicos
MAINS_HZ = 60.0
MAINS_TOLERANCE_HZ = 0.5

# Picos más de 40 dB abajo del mayor se ignoran (lóbulos de la ventana)
PEAK_MIN_REL_MAGNITUDE = 0.01

# Límites del audio recibido
MIN_AUDIO_S = 2.0
MAX_AUDIO_S = 6.0
MIN_AUDIO_RATE = 8000
MAX_AUDIO_RATE = 96000

# Cruce con el acelerómetro: ±5 % (deslizamiento de motores, sección 7.3)
CROSS_TOLERANCE = 0.05


def decode_pcm16(audio_b64: str, sample_rate: int) -> np.ndarray:
    """Decodifica PCM de 16 bits little-endian en base64 a float en [-1, 1]."""
    if not MIN_AUDIO_RATE <= sample_rate <= MAX_AUDIO_RATE:
        raise ValueError("Frecuencia de muestreo de audio fuera de rango.")

    try:
        raw = base64.b64decode(audio_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("El audio no está en base64 válido.") from exc

    if len(raw) % 2:
        raw = raw[:-1]

    signal = np.frombuffer(raw, dtype="<i2").astype(float) / 32768.0
    duration = len(signal) / sample_rate

    if duration < MIN_AUDIO_S:
        raise ValueError("El audio dura menos de 2 segundos.")
    if duration > MAX_AUDIO_S:
        signal = signal[: int(MAX_AUDIO_S * sample_rate)]

    return signal


def _is_mains(freq_hz: float) -> bool:
    k = round(freq_hz / MAINS_HZ)
    return k >= 1 and abs(freq_hz - k * MAINS_HZ) <= MAINS_TOLERANCE_HZ


def find_acoustic_peaks(signal: np.ndarray, sample_rate: int) -> list[float]:
    """Los 11 picos más prominentes entre 10 y 700 Hz (Hann, nfft 2^20)."""
    signal = signal - np.mean(signal)
    nfft = max(ACOUSTIC_NFFT, 1 << int(np.ceil(np.log2(len(signal)))))

    spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal)), n=nfft))
    freqs = np.fft.rfftfreq(nfft, d=1.0 / sample_rate)
    df = freqs[1] - freqs[0]

    band = (freqs >= ACOUSTIC_F_MIN_HZ) & (freqs <= ACOUSTIC_F_MAX_HZ)
    band_idx = np.where(band)[0]
    band_spec = spectrum[band]
    if band_spec.size == 0 or float(np.max(band_spec)) <= 0:
        return []

    peaks, props = scipy.signal.find_peaks(
        band_spec,
        prominence=4.0 * float(np.median(band_spec)),
        distance=max(1, int(round(1.0 / df))),
    )
    if peaks.size == 0:
        return []

    strong = band_spec[peaks] >= PEAK_MIN_REL_MAGNITUDE * float(np.max(band_spec))
    peaks = peaks[strong]
    prominences = props["prominences"][strong]
    top = peaks[np.argsort(prominences)[::-1][:ACOUSTIC_TOP_PEAKS]]

    # Interpolación parabólica para afinar cada pico
    refined = []
    for local in top:
        i = band_idx[local]
        a, b, c = spectrum[i - 1], spectrum[i], spectrum[i + 1]
        denom = a - 2.0 * b + c
        delta = 0.5 * (a - c) / denom if abs(denom) > 1e-12 else 0.0
        refined.append(float(freqs[i] + delta * df))
    return sorted(refined)


def find_fundamental(peaks_hz: list[float]) -> tuple[float | None, int]:
    """Hipótesis armónica: el f0 con más armónicos (k = 1..11, ±1 %).

    Los candidatos son cada pico y sus subarmónicos (p/2, p/3, p/4), porque la
    fundamental puede no sonar. Los múltiplos de 60 Hz no cuentan. Exige al
    menos 3 armónicos; si hay empate gana el f0 más alto (evita subarmónicos).
    """
    harmonics = [p for p in peaks_hz if not _is_mains(p)]

    candidates = {
        p / n
        for p in harmonics
        for n in (1, 2, 3, 4)
        if ACOUSTIC_F_MIN_HZ <= p / n <= ACOUSTIC_F_MAX_HZ and not _is_mains(p / n)
    }

    best_f0: float | None = None
    best_count = 0
    for candidate in sorted(candidates):
        matched: dict[int, float] = {}
        for p in harmonics:
            k = int(round(p / candidate))
            if 1 <= k <= HARMONIC_MAX_K and abs(p - k * candidate) <= HARMONIC_TOLERANCE * k * candidate:
                matched.setdefault(k, p)
        count = len(matched)
        if count >= HARMONIC_MIN_COUNT and count >= best_count:
            # f0 afinado con todos sus armónicos
            best_f0 = float(np.mean([p / k for k, p in matched.items()]))
            best_count = count

    return best_f0, best_count


def fold_frequency(freq_hz: float, fs: float) -> float:
    """Dónde aparece freq_hz muestreada a fs (alias, sección 4)."""
    return abs(freq_hz - round(freq_hz / fs) * fs)


def analyze_audio(audio_b64: str, sample_rate: int) -> dict:
    """Frecuencia de giro por sonido. acoustic_hz es None si no se identificó."""
    signal = decode_pcm16(audio_b64, sample_rate)
    peaks = find_acoustic_peaks(signal, sample_rate)
    f0, count = find_fundamental(peaks)
    return {
        "acoustic_hz": f0,
        "acoustic_harmonics": count if f0 is not None else 0,
        "acoustic_peaks_hz": [round(p, 2) for p in peaks],
    }


def match_accelerometer(f0: float, accel_peaks_hz: list[float], fs: float) -> float | None:
    """Pico del acelerómetro donde debería verse f0 (directo o reflejado), ±5 %."""
    expected = fold_frequency(f0, fs) if f0 > 0.45 * fs else f0
    if expected < 2.0:
        return None
    for peak in accel_peaks_hz:
        if abs(peak - expected) <= CROSS_TOLERANCE * expected:
            return peak
    return None
