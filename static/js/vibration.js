// Medicion de vibraciones en el navegador (Android / iOS).
// Captura muestras del acelerometro con la API DeviceMotion y las envia a la
// API REST de Django (POST /api/analyze/) para el analisis FFT en el servidor.

(function () {
  "use strict";
  function cssColor(variableName, fallback) {
  var value = getComputedStyle(document.documentElement)
    .getPropertyValue(variableName)
    .trim();

  return value || fallback;
}

var COLORS = {
  primary: cssColor("--primary", "#063b68"),
  accent: cssColor("--accent", "#18a6d9"),
  muted: cssColor("--muted", "#64798b"),
  grid: cssColor("--line", "#d8e3eb"),
};

  var ANALYZE_URL = "/api/analyze/";
  var WINDOW_MS = 3000; // ventana de analisis
  var ANALYZE_EVERY_MS = 700; // frecuencia de envio a la API
  var MAX_SCOPE_POINTS = 300;

  var samples = []; // {t, x, y, z}
  var scopeBuffer = []; // magnitud - 9.81 aprox, para el osciloscopio
  var running = false;
  var demoMode = false;
  var demoHz = 0;
  var demoStart = 0;
  var analyzeTimer = null;
  var motionHandler = null;
  var lastAnalyzeInFlight = false;
  var measurementUnit = "acceleration";
  var latestAnalysis = null;

  var els = {
    hz: document.getElementById("hz-value"),
    caption: document.getElementById("hz-caption"),
    rpm: document.getElementById("stat-rpm"),
    fs: document.getElementById("stat-fs"),
    rms: document.getElementById("stat-rms"),
    peak: document.getElementById("stat-peak"),

    rmsLabel: document.getElementById(
  "stat-rms-label"
),

peakLabel: document.getElementById(
  "stat-peak-label"
),

unitDescription: document.getElementById(
  "measurement-unit-description"
),

unitButtons: document.querySelectorAll(
  "[data-vibration-unit]"
),
    dot: document.getElementById("status-dot"),
    statusText: document.getElementById("status-text"),
    start: document.getElementById("btn-start"),
    stop: document.getElementById("btn-stop"),
    pdf: document.getElementById("btn-pdf"),
    scope: document.getElementById("scope"),
    spectrum: document.getElementById("spectrum"),
  };

  var scopeCtx = els.scope.getContext("2d");
  var specCtx = els.spectrum.getContext("2d");

  function setStatus(text, live) {
    els.statusText.textContent = text;
    els.dot.classList.toggle("live", !!live);
  }

  function now() {
    return performance.now();
  }

  function formatMeasurement(
  value,
  decimals,
  unit
) {
  if (
    typeof value !== "number"
    || !Number.isFinite(value)
  ) {
    return "— " + unit;
  }

  return (
    value.toFixed(decimals)
    + " "
    + unit
  );
}


function renderMeasurementUnit() {
  els.unitButtons.forEach(
    function (button) {
      var buttonUnit =
        button.getAttribute(
          "data-vibration-unit"
        );

      var isActive =
        buttonUnit === measurementUnit;

      button.classList.toggle(
        "is-active",
        isActive
      );

      button.setAttribute(
        "aria-pressed",
        isActive ? "true" : "false"
      );
    }
  );


  if (measurementUnit === "velocity") {
    els.rmsLabel.textContent =
      "RMS velocidad";

    els.peakLabel.textContent =
      "Pico velocidad";

    els.unitDescription.textContent =
      "Velocidad vibratoria integrada desde la aceleración";

    els.rms.textContent =
      formatMeasurement(
        latestAnalysis
          ? latestAnalysis.velocity_rms_mms
          : 0,
        3,
        "mm/s"
      );

    els.peak.textContent =
      formatMeasurement(
        latestAnalysis
          ? latestAnalysis.velocity_peak_mms
          : 0,
        3,
        "mm/s"
      );

    return;
  }


  els.rmsLabel.textContent =
    "RMS aceleración";

  els.peakLabel.textContent =
    "Pico aceleración";

  els.unitDescription.textContent =
    "Aceleración vibratoria";

  els.rms.textContent =
    formatMeasurement(
      latestAnalysis
        ? latestAnalysis.rms_ms2
        : 0,
      3,
      "m/s²"
    );

  els.peak.textContent =
    formatMeasurement(
      latestAnalysis
        ? latestAnalysis.peak_ms2
        : 0,
      3,
      "m/s²"
    );
}


function setMeasurementUnit(unit) {
  measurementUnit = (
    unit === "velocity"
      ? "velocity"
      : "acceleration"
  );

  renderMeasurementUnit();
}

  // ---- Captura de muestras reales ----
  function onMotion(event) {
    var a = event.acceleration;
    var incGravity = event.accelerationIncludingGravity;
    var src = a && a.x !== null ? a : incGravity;
    if (!src) return;
    pushSample(src.x || 0, src.y || 0, src.z || 0);
  }

  function pushSample(x, y, z) {
    var t = now();
    samples.push({ t: t, x: x, y: y, z: z });
    var mag = Math.sqrt(x * x + y * y + z * z);
    scopeBuffer.push(mag);
    if (scopeBuffer.length > MAX_SCOPE_POINTS) scopeBuffer.shift();
    // Descartamos muestras fuera de la ventana.
    var cutoff = t - WINDOW_MS;
    while (samples.length && samples[0].t < cutoff) samples.shift();
  }

  // ---- Modo demostracion (senal sintetica) ----
  function demoTick() {
    if (!running || !demoMode) return;
    var t = now();
    // Senal: seno a demoHz + armonico + ruido, muestreado a ~60 Hz.
    var elapsed = (t - demoStart) / 1000;
    var base =
      2.0 * Math.sin(2 * Math.PI * demoHz * elapsed) +
      0.6 * Math.sin(2 * Math.PI * demoHz * 2 * elapsed) +
      (Math.random() - 0.5) * 0.4;
    pushSample(base, base * 0.3, 9.81 + base * 0.2);
    requestAnimationFrame(demoTick);
  }

  // ---- Dibujo del osciloscopio ----
  function drawScope() {
    var c = scopeCtx;
    var w = els.scope.width;
    var h = els.scope.height;
    c.clearRect(0, 0, w, h);
    // linea central
    c.strokeStyle = COLORS.grid;
    c.lineWidth = 1;
    c.beginPath();
    c.moveTo(0, h / 2);
    c.lineTo(w, h / 2);
    c.stroke();

    if (scopeBuffer.length < 2) return;
    // Normalizamos alrededor de la media.
    var mean = 0;
    for (var i = 0; i < scopeBuffer.length; i++) mean += scopeBuffer[i];
    mean /= scopeBuffer.length;
    var maxDev = 0.5;
    for (var j = 0; j < scopeBuffer.length; j++) {
      var d = Math.abs(scopeBuffer[j] - mean);
      if (d > maxDev) maxDev = d;
    }

    c.strokeStyle = COLORS.accent;
    c.lineWidth = 2;
    c.beginPath();
    for (var k = 0; k < scopeBuffer.length; k++) {
      var x = (k / (MAX_SCOPE_POINTS - 1)) * w;
      var norm = (scopeBuffer[k] - mean) / maxDev; // -1..1
      var y = h / 2 - norm * (h / 2 - 8);
      if (k === 0) c.moveTo(x, y);
      else c.lineTo(x, y);
    }
    c.stroke();
  }

  function drawSpectrum(spectrum, dominantHz) {
    var c = specCtx;
    var w = els.spectrum.width;
    var h = els.spectrum.height;
    c.clearRect(0, 0, w, h);
    if (!spectrum || !spectrum.length) return;

    var n = spectrum.length;
    var gap = 3;
    var barW = (w - gap * (n + 1)) / n;

    for (var i = 0; i < n; i++) {
      var amp = spectrum[i].amp; // 0..1
      var barH = Math.max(2, amp * (h - 26));
      var x = gap + i * (barW + gap);
      var y = h - barH - 18;
      var isPeak = Math.abs(spectrum[i].hz - dominantHz) < 0.01;
      c.fillStyle = isPeak ? COLORS.accent : COLORS.primary;
      c.globalAlpha = isPeak ? 1 : 0.55;
      c.fillRect(x, y, barW, barH);
    }
    c.globalAlpha = 1;

    // Etiqueta del pico.
    c.fillStyle = COLORS.muted;
    c.font = "12px Montserrat, sans-serif";
    c.textAlign = "center";
    c.fillText(dominantHz.toFixed(1) + " Hz", w / 2, h - 4);
  }

  // ---- Envio a la API para analisis FFT ----
  function analyze() {
    if (!running || lastAnalyzeInFlight) return;
    if (samples.length < 16) return;
    lastAnalyzeInFlight = true;

    var payload = {
      samples: samples.map(function (s) {
        return { t: s.t, x: s.x, y: s.y, z: s.z };
      }),
    };

    fetch(ANALYZE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json().then(function (data) {
          return { ok: r.ok, data: data };
        });
      })
      .then(function (res) {
        lastAnalyzeInFlight = false;
        if (!res.ok) return;
        updateReadout(res.data);
      })
      .catch(function () {
        lastAnalyzeInFlight = false;
      });
  }

function updateReadout(d) {
  latestAnalysis = d;

  els.hz.textContent =
    d.dominant_hz.toFixed(1);

  els.rpm.textContent =
    Math.round(d.rpm);

  els.fs.textContent =
    d.sample_rate_hz.toFixed(0)
    + " Hz";

  renderMeasurementUnit();

  drawSpectrum(
    d.spectrum,
    d.dominant_hz
  );

  els.pdf.disabled = false;
}

  // ---- Bucle de render ----
  function renderLoop() {
    if (!running) return;
    drawScope();
    requestAnimationFrame(renderLoop);
  }

  // ---- Arranque / parada ----
  function startCommon(label) {
    running = true;
    samples = [];
    scopeBuffer = [];
    latestAnalysis = null;
    renderMeasurementUnit();
    els.start.disabled = true;
    els.pdf.disabled = true;
    els.stop.disabled = false;
    setStatus(label, true);
    analyzeTimer = setInterval(analyze, ANALYZE_EVERY_MS);
    requestAnimationFrame(renderLoop);
  }

  function startReal() {
    demoMode = false;
    motionHandler = onMotion;
    window.addEventListener("devicemotion", motionHandler, true);
    startCommon("Midiendo (sensor)...");

    // Si no llegan datos en 2.5s, avisamos.
    setTimeout(function () {
      if (running && !demoMode && samples.length === 0) {
        setStatus("Sin datos del acelerómetro. Verifica los permisos del sensor.", false);
      }
    }, 2500);
  }

  function startDemo() {
    demoMode = true;
    demoHz = 8 + Math.random() * 22; // 8-30 Hz
    demoStart = now();
    startCommon("Modo demostracion (" + demoHz.toFixed(1) + " Hz)...");
    requestAnimationFrame(demoTick);
    els.caption.textContent = "Senal simulada";
  }

  function downloadMeasurementPdf() {
  if (
    !latestAnalysis
    || samples.length < 8
  ) {
    window.alert(
      "Primero realiza una medición válida."
    );

    return;
  }

  var csrfInput =
    document.querySelector(
      "#measurement-pdf-csrf "
      + "input[name='csrfmiddlewaretoken']"
    );

  if (!csrfInput) {
    window.alert(
      "No se encontró el token de seguridad."
    );

    return;
  }

  var pdfUrl =
    els.pdf.getAttribute(
      "data-pdf-url"
    );

  var originalText =
    els.pdf.textContent;

  els.pdf.disabled = true;
  els.pdf.textContent =
    "Generando...";

  var payload = {
    measurement_unit:
      measurementUnit,

    samples: samples.map(
      function (sample) {
        return {
          t: sample.t,
          x: sample.x,
          y: sample.y,
          z: sample.z,
        };
      }
    ),
  };

  fetch(
    pdfUrl,
    {
      method: "POST",

      credentials:
        "same-origin",

      headers: {
        "Content-Type":
          "application/json",

        "X-CSRFToken":
          csrfInput.value,
      },

      body: JSON.stringify(
        payload
      ),
    }
  )
    .then(function (response) {
      if (!response.ok) {
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (data) {
            throw new Error(
              data.detail
              || (
                "No se pudo "
                + "generar el PDF."
              )
            );
          });
      }

      var disposition =
        response.headers.get(
          "Content-Disposition"
        )
        || "";

      var filename =
        "SMAV_INAHER_"
        + "medicion_vibratoria.pdf";

      var match =
        disposition.match(
          /filename="?([^"]+)"?/i
        );

      if (
        match
        && match[1]
      ) {
        filename =
          match[1];
      }

      return response
        .blob()
        .then(
          function (blob) {
            return {
              blob: blob,
              filename: filename,
            };
          }
        );
    })
    .then(function (result) {
      var objectUrl =
        URL.createObjectURL(
          result.blob
        );

      var link =
        document.createElement(
          "a"
        );

      link.href =
        objectUrl;

      link.download =
        result.filename;

      document.body.appendChild(
        link
      );

      link.click();

      link.remove();

      window.setTimeout(
        function () {
          URL.revokeObjectURL(
            objectUrl
          );
        },
        1000
      );
    })
    .catch(function (error) {
      window.alert(
        error.message
        || (
          "No se pudo "
          + "generar el PDF."
        )
      );
    })
    .finally(function () {
      els.pdf.textContent =
        originalText;

      els.pdf.disabled =
        !latestAnalysis
        || samples.length < 8;
    });
}

  function stop() {
    running = false;
    demoMode = false;
    if (motionHandler) {
      window.removeEventListener("devicemotion", motionHandler, true);
      motionHandler = null;
    }
    if (analyzeTimer) {
      clearInterval(analyzeTimer);
      analyzeTimer = null;
    }
    els.start.disabled = false;

    els.pdf.disabled =
      !latestAnalysis
        || samples.length < 8;

    els.stop.disabled = true;
    setStatus("Detenido", false);
  }

  // iOS 13+ requiere solicitar permiso tras un gesto del usuario.
  function requestMotionPermission() {
    if (
      typeof DeviceMotionEvent !== "undefined" &&
      typeof DeviceMotionEvent.requestPermission === "function"
    ) {
      return DeviceMotionEvent.requestPermission().then(function (state) {
        return state === "granted";
      });
    }
    return Promise.resolve(true);
  }

  els.unitButtons.forEach(
  function (button) {
    button.addEventListener(
      "click",
      function () {
        setMeasurementUnit(
          button.getAttribute(
            "data-vibration-unit"
          )
        );
      }
    );
  }
);

  els.start.addEventListener("click", function () {
    requestMotionPermission()
      .then(function (granted) {
        if (!granted) {
          setStatus("Permiso de movimiento denegado.", false);
          return;
        }
        startReal();
      })
      .catch(function () {
        setStatus("No se pudo acceder al acelerometro.", false);
      });
  });

 els.pdf.addEventListener(
  "click",
  function () {
    downloadMeasurementPdf();
  }
);

  els.stop.addEventListener("click", stop);

  // Estado inicial de los lienzos.
setMeasurementUnit("acceleration");
drawScope();
drawSpectrum([], 0);
})();