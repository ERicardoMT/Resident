from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


PRIMARY = colors.HexColor("#063B68")
PRIMARY_DARK = colors.HexColor("#031C33")
ACCENT = colors.HexColor("#18A6D9")
TEXT = colors.HexColor("#102F49")
MUTED = colors.HexColor("#64798B")
LINE = colors.HexColor("#D8E3EB")
SURFACE = colors.HexColor("#F6F9FB")
SPECTRUM_BAR = colors.HexColor("#8BA9BD")


def _format_number(
    value: Any,
    decimals: int = 2,
) -> str:
    try:
        number = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return "—"

    return f"{number:.{decimals}f}"


def _draw_logo(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    max_width: float,
    max_height: float,
) -> None:
    """
    Dibuja el logo local de INAHER si está disponible.
    """

    logo_path = (
        Path(settings.BASE_DIR)
        / "static"
        / "img"
        / "inaher-logo.png"
    )

    if not logo_path.exists():
        return

    try:
        image = ImageReader(
            str(logo_path)
        )

        image_width, image_height = (
            image.getSize()
        )

        scale = min(
            max_width / image_width,
            max_height / image_height,
        )

        width = image_width * scale
        height = image_height * scale

        pdf.drawImage(
            image,
            x,
            y,
            width=width,
            height=height,
            mask="auto",
        )

    except Exception:
        # El reporte debe seguir funcionando
        # aunque el logo no pudiera cargarse.
        return


def _draw_metric_card(
    pdf: canvas.Canvas,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    value: str,
) -> None:
    pdf.setFillColor(SURFACE)
    pdf.setStrokeColor(LINE)

    pdf.roundRect(
        x,
        y,
        width,
        height,
        8,
        fill=1,
        stroke=1,
    )

    pdf.setFillColor(MUTED)
    pdf.setFont(
        "Helvetica-Bold",
        8,
    )

    pdf.drawString(
        x + 12,
        y + height - 17,
        label.upper(),
    )

    pdf.setFillColor(PRIMARY)
    pdf.setFont(
        "Helvetica-Bold",
        14,
    )

    pdf.drawString(
        x + 12,
        y + 14,
        value,
    )


def _draw_spectrum(
    pdf: canvas.Canvas,
    analysis: dict[str, Any],
    *,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    spectrum = analysis.get(
        "spectrum",
        [],
    )

    pdf.setFillColor(TEXT)
    pdf.setFont(
        "Helvetica-Bold",
        11,
    )

    pdf.drawString(
        x,
        y + height + 17,
        "Espectro FFT normalizado",
    )

    pdf.setFillColor(SURFACE)
    pdf.setStrokeColor(LINE)

    pdf.roundRect(
        x,
        y,
        width,
        height,
        8,
        fill=1,
        stroke=1,
    )

    if not spectrum:
        pdf.setFillColor(MUTED)
        pdf.setFont(
            "Helvetica",
            9,
        )

        pdf.drawCentredString(
            x + width / 2,
            y + height / 2,
            "Sin datos de espectro",
        )

        return

    chart_left = x + 18
    chart_right = x + width - 18
    chart_bottom = y + 23
    chart_top = y + height - 18

    chart_width = (
        chart_right
        - chart_left
    )

    chart_height = (
        chart_top
        - chart_bottom
    )

    dominant_hz = float(
        analysis.get(
            "dominant_hz",
            0,
        )
    )

    closest_index = min(
        range(len(spectrum)),
        key=lambda index: abs(
            float(
                spectrum[index].get(
                    "hz",
                    0,
                )
            )
            - dominant_hz
        ),
    )

    gap = 1.5

    bar_width = max(
        1.0,
        (
            chart_width
            - (
                gap
                * (
                    len(spectrum)
                    - 1
                )
            )
        )
        / len(spectrum),
    )

    pdf.setStrokeColor(LINE)

    pdf.line(
        chart_left,
        chart_bottom,
        chart_right,
        chart_bottom,
    )

    for index, point in enumerate(
        spectrum
    ):
        amplitude = float(
            point.get(
                "amp",
                0,
            )
        )

        amplitude = max(
            0,
            min(
                amplitude,
                1,
            ),
        )

        bar_height = max(
            1,
            amplitude
            * chart_height,
        )

        bar_x = (
            chart_left
            + (
                index
                * (
                    bar_width
                    + gap
                )
            )
        )

        if index == closest_index:
            pdf.setFillColor(
                ACCENT
            )
        else:
            pdf.setFillColor(
                SPECTRUM_BAR
            )

        pdf.rect(
            bar_x,
            chart_bottom,
            bar_width,
            bar_height,
            fill=1,
            stroke=0,
        )

    min_hz = float(
        spectrum[0].get(
            "hz",
            0,
        )
    )

    max_hz = float(
        spectrum[-1].get(
            "hz",
            0,
        )
    )

    pdf.setFillColor(MUTED)
    pdf.setFont(
        "Helvetica",
        7,
    )

    pdf.drawString(
        chart_left,
        y + 8,
        f"{min_hz:.1f} Hz",
    )

    pdf.drawRightString(
        chart_right,
        y + 8,
        f"{max_hz:.1f} Hz",
    )

    pdf.setFillColor(ACCENT)
    pdf.setFont(
        "Helvetica-Bold",
        8,
    )

    pdf.drawCentredString(
        x + width / 2,
        y + 8,
        (
            "Dominante: "
            f"{dominant_hz:.2f} Hz"
        ),
    )


def build_measurement_pdf(
    analysis: dict[str, Any],
    *,
    selected_unit: str = "acceleration",
) -> BytesIO:
    """
    Genera el reporte PDF de una medición vibratoria.
    """

    buffer = BytesIO()

    page_width, page_height = (
        LETTER
    )

    pdf = canvas.Canvas(
        buffer,
        pagesize=LETTER,
        pageCompression=1,
    )

    pdf.setTitle(
        "Reporte de medición vibratoria SMAV INAHER"
    )

    margin = 38
    header_height = 108

    # =====================================================
    # Encabezado
    # =====================================================

    pdf.setFillColor(
        PRIMARY_DARK
    )

    pdf.rect(
        0,
        page_height - header_height,
        page_width,
        header_height,
        fill=1,
        stroke=0,
    )

    pdf.setFillColor(
        colors.white
    )

    pdf.roundRect(
        margin,
        page_height - 80,
        125,
        48,
        7,
        fill=1,
        stroke=0,
    )

    _draw_logo(
        pdf,
        margin + 10,
        page_height - 70,
        105,
        28,
    )

    pdf.setFillColor(
        colors.white
    )

    pdf.setFont(
        "Helvetica-Bold",
        18,
    )

    pdf.drawString(
        185,
        page_height - 47,
        "Reporte de medición vibratoria",
    )

    pdf.setFont(
        "Helvetica",
        9,
    )

    pdf.setFillColor(
        colors.HexColor(
            "#D8ECF7"
        )
    )

    pdf.drawString(
        185,
        page_height - 65,
        "SMAV · Sistema de Medición y Análisis Vibratorio",
    )

    generated_at = (
        timezone.localtime()
    )

    pdf.drawString(
        185,
        page_height - 82,
        generated_at.strftime(
            "%d/%m/%Y  %H:%M:%S"
        ),
    )

    # =====================================================
    # Información de medición
    # =====================================================

    current_y = (
        page_height
        - header_height
        - 30
    )

    pdf.setFillColor(TEXT)
    pdf.setFont(
        "Helvetica-Bold",
        13,
    )

    pdf.drawString(
        margin,
        current_y,
        "Resultados de la medición",
    )

    current_y -= 16

    selected_label = (
        "Velocidad vibratoria"
        if selected_unit
        == "velocity"
        else "Aceleración vibratoria"
    )

    pdf.setFillColor(MUTED)
    pdf.setFont(
        "Helvetica",
        8.5,
    )

    pdf.drawString(
        margin,
        current_y,
        (
            "Unidad seleccionada en la interfaz: "
            + selected_label
        ),
    )

    current_y -= 69

    gap = 12

    card_width = (
        page_width
        - (
            margin
            * 2
        )
        - gap
    ) / 2

    card_height = 50

    metrics = [
        (
            "Frecuencia dominante",
            (
                _format_number(
                    analysis.get(
                        "dominant_hz"
                    ),
                    2,
                )
                + " Hz"
            ),
        ),
        (
            "RPM estimadas",
            _format_number(
                analysis.get(
                    "rpm"
                ),
                0,
            ),
        ),
        (
            "Frecuencia de muestreo",
            (
                _format_number(
                    analysis.get(
                        "sample_rate_hz"
                    ),
                    1,
                )
                + " Hz"
            ),
        ),
        (
            "Duración de ventana",
            (
                _format_number(
                    analysis.get(
                        "duration_s"
                    ),
                    2,
                )
                + " s"
            ),
        ),
        (
            "RMS aceleración",
            (
                _format_number(
                    analysis.get(
                        "rms_ms2"
                    ),
                    4,
                )
                + " m/s²"
            ),
        ),
        (
            "Pico aceleración",
            (
                _format_number(
                    analysis.get(
                        "peak_ms2"
                    ),
                    4,
                )
                + " m/s²"
            ),
        ),
        (
            "RMS velocidad",
            (
                _format_number(
                    analysis.get(
                        "velocity_rms_mms"
                    ),
                    4,
                )
                + " mm/s"
            ),
        ),
        (
            "Pico velocidad",
            (
                _format_number(
                    analysis.get(
                        "velocity_peak_mms"
                    ),
                    4,
                )
                + " mm/s"
            ),
        ),
    ]

    for index, (
        label,
        value,
    ) in enumerate(metrics):
        column = index % 2
        row = index // 2

        x = (
            margin
            + column
            * (
                card_width
                + gap
            )
        )

        y = (
            current_y
            - (
                row
                * (
                    card_height
                    + gap
                )
            )
        )

        _draw_metric_card(
            pdf,
            x=x,
            y=y,
            width=card_width,
            height=card_height,
            label=label,
            value=value,
        )

    current_y -= (
        4
        * (
            card_height
            + gap
        )
    )

    # =====================================================
    # Datos adicionales
    # =====================================================

    pdf.setFillColor(TEXT)
    pdf.setFont(
        "Helvetica-Bold",
        10,
    )

    pdf.drawString(
        margin,
        current_y + 4,
        "Información de adquisición",
    )

    pdf.setFillColor(MUTED)
    pdf.setFont(
        "Helvetica",
        8,
    )

    sample_count = int(
        analysis.get(
            "sample_count",
            0,
        )
        or 0
    )

    pdf.drawString(
        margin,
        current_y - 11,
        (
            f"Muestras analizadas: "
            f"{sample_count}"
        ),
    )

    pdf.drawString(
        margin + 170,
        current_y - 11,
        (
            "RMS: "
            + _format_number(
                analysis.get(
                    "rms_g"
                ),
                5,
            )
            + " g"
        ),
    )

    pdf.drawString(
        margin + 315,
        current_y - 11,
        (
            "Pico: "
            + _format_number(
                analysis.get(
                    "peak_g"
                ),
                5,
            )
            + " g"
        ),
    )

    # =====================================================
    # Espectro FFT
    # =====================================================

    spectrum_y = 92
    spectrum_height = 135

    _draw_spectrum(
        pdf,
        analysis,
        x=margin,
        y=spectrum_y,
        width=(
            page_width
            - 2
            * margin
        ),
        height=spectrum_height,
    )

    # =====================================================
    # Aviso y pie
    # =====================================================

    pdf.setFillColor(MUTED)
    pdf.setFont(
        "Helvetica",
        7,
    )

    pdf.drawString(
        margin,
        59,
        (
            "Resultado orientativo basado en los datos "
            "capturados por el sensor del dispositivo."
        ),
    )

    pdf.drawString(
        margin,
        48,
        (
            "No sustituye una evaluación instrumental "
            "certificada ni asesoría de ingeniería."
        ),
    )

    pdf.setStrokeColor(LINE)

    pdf.line(
        margin,
        37,
        page_width - margin,
        37,
    )

    pdf.setFillColor(PRIMARY)
    pdf.setFont(
        "Helvetica-Bold",
        7.5,
    )

    pdf.drawString(
        margin,
        24,
        "INAHER · SMAV",
    )

    pdf.setFillColor(MUTED)
    pdf.setFont(
        "Helvetica",
        7.5,
    )

    pdf.drawRightString(
        page_width - margin,
        24,
        "Reporte generado automáticamente",
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return buffer