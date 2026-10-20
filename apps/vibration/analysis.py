"""Módulo de análisis de vibraciones para SMAV.

Delega el procesamiento digital de señales al motor en apps.vibration.dsp,
conforme a la Sección 7 del Libro Maestro de SMAV.
"""

from __future__ import annotations

from typing import Any, Sequence

from .dsp import process_vibration_samples


def analyze_samples(
    samples: Sequence[dict[str, Any]],
    rpm_placa: float | int | None = None,
    gravity_included: bool = False,
    user_agent: str = "",
) -> dict[str, Any]:
    """
    Procesa muestras de acelerómetro ({t, x, y, z}) mediante remuestreo uniforme,
    filtrado Butterworth 2 Hz - 0.45*fs, espectro Welch, factor de cresta y
    resolución de alias con RPM de placa.
    """
    return process_vibration_samples(
        samples=samples,
        rpm_placa=rpm_placa,
        gravity_included=gravity_included,
        user_agent=user_agent,
    )
