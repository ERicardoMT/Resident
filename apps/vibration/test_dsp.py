"""Pruebas automáticas mínimas del motor DSP conforme a la Sección 7.7 del Libro Maestro.

Valida:
1. Seno 14.4 Hz, 1.0 m/s² pico a 60 Hz -> RMS 0.707 +- 2%, pico 1.0 +- 2%, f = 14.4 +- 0.1, status 'clear'.
2. Seno 41.7 Hz a 60 Hz con rpm_placa = 2500 -> 'aliased_confirmed', dominant 41.7 +- 0.5.
3. Ruido blanco -> 'unclear', dominant None.
4. Seno + impulsos cada 1 s -> impacts = True.
5. Seno 1 Hz de 1 m/s² -> RMS filtrado < 0.05 (la banda lo elimina).
6. Cerca del límite (0.40*fs < f <= 0.45*fs) -> 'near_limit'.
7. Coincidencia directa con placa en rango -> 'confirmed'.
8. Placa que no coincide con el espectro -> 'not_found', dominant None.
9. Seno 28.7 Hz (arriba de 0.45*fs) -> la amplitud sí se mide.
"""

import unittest
import numpy as np
import pytest

from apps.vibration.dsp import process_vibration_samples


def generate_samples(
    times: np.ndarray,
    x: np.ndarray,
    y: np.ndarray | None = None,
    z: np.ndarray | None = None,
) -> list[dict]:
    """Convierte arrays de tiempo y aceleración a la estructura esperada de muestras."""
    if y is None:
        y = np.zeros_like(x)
    if z is None:
        z = np.zeros_like(x)

    return [
        {
            "t": float(t * 1000.0),
            "x": float(vx),
            "y": float(vy),
            "z": float(vz),
        }
        for t, vx, vy, vz in zip(times, x, y, z)
    ]


class DspMinimumAutomatedTests(unittest.TestCase):
    """Casos de prueba de la Sección 7.7 del Libro Maestro."""

    def setUp(self):
        self.fs = 60.0
        self.duration = 10.0
        self.times = np.arange(int(round(self.fs * self.duration))) / self.fs

    def test_1_sine_14_4_hz(self):
        """Seno 14.4 Hz, 1.0 m/s² pico a 60 Hz -> RMS 0.707 +- 2%, pico 1.0 +- 2%, f = 14.4 +- 0.1, clear."""
        f0 = 14.4
        # Señal aplicada en el eje Z (perpendicular al chasis)
        z = 1.0 * np.sin(2.0 * np.pi * f0 * self.times)
        samples = generate_samples(self.times, x=np.zeros_like(z), z=z)

        res = process_vibration_samples(samples)

        # RMS 0.707 +- 2%
        expected_rms = 1.0 / np.sqrt(2.0)
        self.assertAlmostEqual(res["rms_ms2"], expected_rms, delta=expected_rms * 0.02)

        # Pico 1.0 +- 2%
        self.assertAlmostEqual(res["peak_ms2"], 1.0, delta=0.02)

        # Frecuencia 14.4 +- 0.1 Hz
        self.assertIsNotNone(res["dominant_hz"])
        self.assertAlmostEqual(res["dominant_hz"], f0, delta=0.1)

        # Estado 'clear'
        self.assertEqual(res["frequency_status"], "clear")
        self.assertEqual(res["level"], "medium")
        self.assertFalse(res["impacts"])

    def test_2_alias_with_rpm_placa(self):
        """Seno 41.7 Hz a 60 Hz con rpm_placa = 2500 -> aliased_confirmed, dominant 41.7 +- 0.5."""
        f_real = 41.7
        # A 60 Hz de muestreo, 41.7 Hz aparece reflejada en |41.7 - 60| = 18.3 Hz
        z = 1.0 * np.sin(2.0 * np.pi * f_real * self.times)
        samples = generate_samples(self.times, z=z, x=np.zeros_like(z))

        res = process_vibration_samples(samples, rpm_placa=2500)

        self.assertEqual(res["frequency_status"], "aliased_confirmed")
        self.assertIsNotNone(res["dominant_hz"])
        self.assertAlmostEqual(res["dominant_hz"], 41.7, delta=0.5)
        self.assertIn("coincide con la placa", res["frequency_message"].lower())

    def test_3_white_noise_unclear(self):
        """Ruido blanco -> unclear, dominant null."""
        np.random.seed(42)
        noise = np.random.normal(0, 0.05, len(self.times))
        samples = generate_samples(self.times, z=noise, x=np.zeros_like(noise))

        res = process_vibration_samples(samples)

        self.assertEqual(res["frequency_status"], "unclear")
        self.assertIsNone(res["dominant_hz"])
        self.assertIsNone(res["dominant_rpm"])

    def test_4_impacts_crest_factor(self):
        """Seno + impulsos cada 1 s -> impacts = true."""
        z = 1.0 * np.sin(2.0 * np.pi * 14.4 * self.times)
        # Inyectar golpes fuertes cada 1 segundo
        for i in range(1, int(self.duration)):
            idx = int(round(i * self.fs))
            z[idx] += 10.0

        samples = generate_samples(self.times, z=z, x=np.zeros_like(z))
        res = process_vibration_samples(samples)

        self.assertTrue(res["impacts"])
        self.assertGreater(res["crest"], 4.0)

    def test_5_sine_1_hz_eliminated_by_filter(self):
        """Seno 1 Hz de 1 m/s² -> RMS filtrado < 0.05 (la banda 2 Hz lo elimina)."""
        z = 1.0 * np.sin(2.0 * np.pi * 1.0 * self.times)
        samples = generate_samples(self.times, z=z, x=np.zeros_like(z))

        res = process_vibration_samples(samples)

        self.assertLess(res["rms_ms2"], 0.05)

    def test_6_near_limit_frequency(self):
        """Frecuencia entre 0.40*fs y 0.45*fs (ej. 25.5 Hz a 60 Hz) -> near_limit."""
        f_near = 25.5
        z = 1.0 * np.sin(2.0 * np.pi * f_near * self.times)
        samples = generate_samples(self.times, z=z, x=np.zeros_like(z))

        res = process_vibration_samples(samples)

        self.assertEqual(res["frequency_status"], "near_limit")
        self.assertAlmostEqual(res["dominant_hz"], f_near, delta=0.2)

    def test_7_confirmed_in_range_with_placa(self):
        """Frecuencia directa dentro de rango con placa (ej. 14.4 Hz, rpm 864) -> confirmed."""
        f_direct = 14.4
        z = 1.0 * np.sin(2.0 * np.pi * f_direct * self.times)
        samples = generate_samples(self.times, z=z, x=np.zeros_like(z))

        res = process_vibration_samples(samples, rpm_placa=864)

        self.assertEqual(res["frequency_status"], "confirmed")
        self.assertAlmostEqual(res["dominant_hz"], 14.4, delta=0.1)

    def test_8_placa_does_not_match(self):
        """Seno 14.4 Hz con rpm_placa = 2500 (esperado 18.3 reflejado) -> not_found, dominant null."""
        z = 1.0 * np.sin(2.0 * np.pi * 14.4 * self.times)
        samples = generate_samples(self.times, z=z, x=np.zeros_like(z))

        res = process_vibration_samples(samples, rpm_placa=2500)

        self.assertEqual(res["frequency_status"], "not_found")
        self.assertIsNone(res["dominant_hz"])
        self.assertIsNone(res["dominant_rpm"])

    def test_9_amplitude_above_band_is_measured(self):
        """Seno 28.7 Hz (taladro 1,720 rpm) a 60 Hz -> la frecuencia no se reporta, la vibración sí (RMS 0.707 +- 5%)."""
        z = 1.0 * np.sin(2.0 * np.pi * 28.7 * self.times)
        samples = generate_samples(self.times, z=z, x=np.zeros_like(z))

        res = process_vibration_samples(samples)

        expected_rms = 1.0 / np.sqrt(2.0)
        self.assertAlmostEqual(res["rms_ms2"], expected_rms, delta=expected_rms * 0.05)
        self.assertEqual(res["level"], "medium")
        self.assertNotIn(res["frequency_status"], ("clear", "confirmed"))


if __name__ == "__main__":
    unittest.main()

