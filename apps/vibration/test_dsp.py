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
10-14. Micrófono (7.5): audio con armónicos 83.4/125.1/166.8 + red 60/120 -> 41.7 Hz;
       solo red o ruido -> nada; cruce con el acelerómetro (alias confirmado o lecturas distintas).
"""

import base64
import unittest
import numpy as np
import pytest

from apps.vibration.acoustic import analyze_audio
from apps.vibration.dsp import process_vibration_samples

AUDIO_RATE = 48000


def synthetic_audio(tones, mains=(), noise=0.02, seconds=5.0, seed=0):
    """Audio PCM 16 bits en base64: tonos [(Hz, amplitud)], red eléctrica y ruido."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * AUDIO_RATE)) / AUDIO_RATE
    signal = noise * rng.normal(size=t.size)
    for freq, amp in list(tones) + list(mains):
        signal += amp * np.sin(2.0 * np.pi * freq * t)
    pcm = (np.clip(signal, -1.0, 1.0) * 32767).astype("<i2")
    return base64.b64encode(pcm.tobytes()).decode("ascii")


# Torno a 2,500 rpm: armónicos 2, 3 y 4 de 41.7 Hz (la fundamental no suena)
LATHE_TONES = [(83.4, 0.10), (125.1, 0.07), (166.8, 0.05)]
MAINS_HUM = [(60.0, 0.15), (120.0, 0.09)]


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


    def test_10_acoustic_harmonics_find_fundamental(self):
        """Audio con armónicos 83.4, 125.1, 166.8 Hz y 60/120 Hz de red -> acoustic_hz = 41.7 +- 0.3 (7.7)."""
        res = analyze_audio(synthetic_audio(LATHE_TONES, MAINS_HUM), AUDIO_RATE)

        self.assertIsNotNone(res["acoustic_hz"])
        self.assertAlmostEqual(res["acoustic_hz"], 41.7, delta=0.3)
        self.assertGreaterEqual(res["acoustic_harmonics"], 3)

    def test_11_acoustic_mains_or_noise_only(self):
        """Solo red eléctrica (60/120/180/240) o solo ruido -> no se identifica frecuencia."""
        mains = [(60.0, 0.2), (120.0, 0.12), (180.0, 0.08), (240.0, 0.06)]
        self.assertIsNone(analyze_audio(synthetic_audio([], mains), AUDIO_RATE)["acoustic_hz"])
        self.assertIsNone(analyze_audio(synthetic_audio([], noise=0.1), AUDIO_RATE)["acoustic_hz"])

    def test_12_acoustic_confirms_alias_without_placa(self):
        """Torno: acelerómetro ve 18.3 Hz (alias de 41.7) y el sonido marca 41.7 -> aliased_confirmed sin placa."""
        z = 1.0 * np.sin(2.0 * np.pi * 41.7 * self.times)
        samples = generate_samples(self.times, z=z, x=np.zeros_like(z))

        res = process_vibration_samples(
            samples,
            audio_pcm16=synthetic_audio(LATHE_TONES, MAINS_HUM),
            audio_sample_rate=AUDIO_RATE,
        )

        self.assertEqual(res["frequency_status"], "aliased_confirmed")
        self.assertAlmostEqual(res["dominant_hz"], 41.7, delta=0.3)
        self.assertEqual(res["acoustic_confidence"], "high")
        # El micrófono no cambia la amplitud
        self.assertAlmostEqual(res["rms_ms2"], 1.0 / np.sqrt(2.0), delta=0.02)

    def test_13_acoustic_and_accelerometer_disagree(self):
        """Acelerómetro 14.4 Hz y sonido 41.7 Hz -> confianza baja, se queda la lectura del movimiento."""
        z = 1.0 * np.sin(2.0 * np.pi * 14.4 * self.times)
        samples = generate_samples(self.times, z=z, x=np.zeros_like(z))

        res = process_vibration_samples(
            samples,
            audio_pcm16=synthetic_audio(LATHE_TONES, MAINS_HUM),
            audio_sample_rate=AUDIO_RATE,
        )

        self.assertEqual(res["frequency_status"], "clear")
        self.assertAlmostEqual(res["dominant_hz"], 14.4, delta=0.1)
        self.assertEqual(res["acoustic_confidence"], "low")
        self.assertIn("Dos lecturas distintas", res["frequency_note"])

    def test_14_acoustic_confirms_in_range(self):
        """Compresor 14.4 Hz: el sonido con armónicos de 14.4 lo confirma -> confirmed."""
        tones = [(14.4 * k, 0.1 / k) for k in (2, 3, 4, 5)]
        z = 1.0 * np.sin(2.0 * np.pi * 14.4 * self.times)
        samples = generate_samples(self.times, z=z, x=np.zeros_like(z))

        res = process_vibration_samples(
            samples,
            audio_pcm16=synthetic_audio(tones, MAINS_HUM),
            audio_sample_rate=AUDIO_RATE,
        )

        self.assertEqual(res["frequency_status"], "confirmed")
        self.assertAlmostEqual(res["dominant_hz"], 14.4, delta=0.1)
        self.assertEqual(res["acoustic_confidence"], "high")


if __name__ == "__main__":
    unittest.main()

