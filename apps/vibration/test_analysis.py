import unittest

import numpy as np

from apps.vibration.analysis import (
    analyze_samples,
)


class AnalyzeSamplesTests(
    unittest.TestCase
):

    SAMPLE_RATE_HZ = 200.0
    DURATION_SECONDS = 4.0

    def build_signal(
        self,
        frequency_hz,
        *,
        gravity=False,
    ):
        """
        Genera una vibración senoidal conocida.

        Usamos 200 Hz de muestreo para que incluso
        una señal de 50 Hz pueda analizarse
        correctamente durante las pruebas.
        """

        sample_count = int(
            self.SAMPLE_RATE_HZ
            * self.DURATION_SECONDS
        )

        times = (
            np.arange(sample_count)
            / self.SAMPLE_RATE_HZ
        )

        vibration = (
            2.0
            * np.sin(
                2.0
                * np.pi
                * frequency_hz
                * times
            )
        )

        samples = []

        for index, time_s in enumerate(times):

            value = vibration[index]

            if gravity:

                z_value = (
                    9.80665
                    + (
                        value
                        * 0.20
                    )
                )

            else:

                z_value = (
                    value
                    * 0.20
                )

            samples.append(
                {
                    "t": float(
                        time_s
                        * 1000.0
                    ),
                    "x": float(value),
                    "y": float(
                        value
                        * 0.35
                    ),
                    "z": float(
                        z_value
                    ),
                }
            )

        return samples

    def test_known_frequencies_without_gravity(
        self,
    ):
        """
        Este test detecta específicamente
        el antiguo problema de 2f producido
        por sqrt(x² + y² + z²).
        """

        frequencies = (
            5.0,
            10.0,
            15.0,
            25.0,
            30.0,
            50.0,
        )

        for frequency in frequencies:

            with self.subTest(
                frequency=frequency
            ):

                samples = self.build_signal(
                    frequency
                )

                result = analyze_samples(
                    samples
                )

                self.assertAlmostEqual(
                    result[
                        "dominant_hz"
                    ],
                    frequency,
                    delta=0.30,
                )

                self.assertAlmostEqual(
                    result["rpm"],
                    frequency * 60.0,
                    delta=20.0,
                )

    def test_frequency_with_gravity_offset(
        self,
    ):
        """
        Simula accelerationIncludingGravity.
        """

        frequency = 15.0

        samples = self.build_signal(
            frequency,
            gravity=True,
        )

        result = analyze_samples(
            samples
        )

        self.assertAlmostEqual(
            result["dominant_hz"],
            frequency,
            delta=0.30,
        )


if __name__ == "__main__":
    unittest.main()