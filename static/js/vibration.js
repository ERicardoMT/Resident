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
  var SIMPLE_MEASUREMENT_DURATION_MS =
    10000;

  var samples = []; // {t, x, y, z}
  // -----------------------------------------------------
// Medición completa de 10 segundos
// -----------------------------------------------------
  var measurementSamples = [];
  var completedMeasurementSamples = [];
  var isMeasurementCapturing = false;
  var measurementStartedAt = null;
  var scopeBuffer = []; // magnitud - 9.81 aprox, para el osciloscopio
  var running = false;
  var analyzeTimer = null;
  var motionHandler = null;
  var lastAnalyzeInFlight = false;
  var measurementUnit = "acceleration";
  var latestAnalysis = null;
  var preparedShareFile = null;

  function startFullMeasurementCapture() {
    measurementSamples = [];
    completedMeasurementSamples = [];

    measurementStartedAt = null;
    isMeasurementCapturing = true;
}


function stopFullMeasurementCapture() {
    isMeasurementCapturing = false;

    if (!measurementSamples.length) {
        completedMeasurementSamples = [];
        measurementStartedAt = null;

        return [];
    }

    var startTime = measurementSamples[0].t;

    completedMeasurementSamples =
        measurementSamples.filter(function (sample) {
            return (
                sample.t - startTime
                <= SIMPLE_MEASUREMENT_DURATION_MS
            );
        });

    measurementStartedAt = null;

    return completedMeasurementSamples.slice();
}


function cancelFullMeasurementCapture() {
    isMeasurementCapturing = false;

    measurementStartedAt = null;
    measurementSamples = [];
    completedMeasurementSamples = [];
}

  var els = {
    hz: document.getElementById("hz-value"),
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
    pdf:
      document.getElementById(
        "btn-pdf"
      ),
    
    sharePdf:
      document.getElementById(
        "btn-share-pdf"
      ),

    scope:
      document.getElementById(
        "scope"
    ),
    spectrum: document.getElementById("spectrum"),
        // Nueva vista sencilla
    simpleCard: document.getElementById(
      "measurement-simple-card"
    ),

    simpleKicker: document.getElementById(
      "measurement-simple-kicker"
    ),

    simpleHelp: document.getElementById(
      "measurement-simple-help"
    ),

    simpleProgressBarFill: document.getElementById(
      "measurement-simple-progressbar-fill"
    ),

    advancedPanel: document.getElementById(
      "measurement-advanced"
    ),
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


var SMAV_SIMPLE_TICK_MS =
  100;

var smavSimpleTimer =
  null;

var smavSimpleStartedAt =
  0;

  
function smavSetSimpleMeasuring() {

  if (els.simpleKicker) {

    els.simpleKicker.textContent =
      "MIDIENDO...";

  }


  if (els.simpleHelp) {

    els.simpleHelp.textContent =
      "Mantén el teléfono quieto · 10 segundos";

  }
}

function smavSetSimpleError(
  message
) {

  if (els.simpleKicker) {

    els.simpleKicker.textContent =
      "MEDICIÓN NO VÁLIDA";

  }


  if (els.simpleHelp) {

    els.simpleHelp.textContent =
      message
      ||
      "No se pudo completar la medición.";

  }


  if (els.simpleProgressBarFill) {

    els.simpleProgressBarFill.style.width =
      "0%";

  }
}




function smavSetSimpleFinished() {

  if (els.simpleKicker) {

    els.simpleKicker.textContent =
      "MEDICIÓN COMPLETADA";

  }


  if (els.simpleHelp) {

    els.simpleHelp.textContent =
      "Resultado obtenido en 10 segundos";

  }


  if (els.simpleProgressBarFill) {

    els.simpleProgressBarFill.style.width =
      "100%";

  }
}


function smavStopSimpleMeasurementUi() {

  if (
    smavSimpleTimer !== null
  ) {

    clearInterval(
      smavSimpleTimer
    );

    smavSimpleTimer =
      null;
  }
}

function smavStartSimpleMeasurementUi() {

  smavStopSimpleMeasurementUi();



  var bar =
    els.simpleProgressBarFill;

  var help =
    els.simpleHelp;


  smavSimpleStartedAt =
    Date.now();


  if (bar) {

    bar.style.width =
      "0%";

  }


  smavSetSimpleMeasuring();


  smavSimpleTimer =
    setInterval(
      function () {

        var elapsed =
          Date.now()
          -
          smavSimpleStartedAt;


        var progress =
          elapsed
          /
          SIMPLE_MEASUREMENT_DURATION_MS


        progress =
          Math.max(
            0,
            Math.min(
              1,
              progress
            )
          );


        var percentage =
          progress * 100;


        if (bar) {

          bar.style.width =
            percentage + "%";

        }


        var remainingMilliseconds =
          Math.max(
            0,
            SIMPLE_MEASUREMENT_DURATION_MS
            -
            elapsed
          );


        var remainingSeconds =
          Math.ceil(
            remainingMilliseconds
            /
            1000
          );


        if (
          help
          &&
          progress < 1
        ) {

          help.textContent =
            "Mantén el teléfono quieto · "
            +
            remainingSeconds
            +
            (
              remainingSeconds === 1
                ? " segundo"
                : " segundos"
            );

        }


if (progress >= 1) {

  smavStopSimpleMeasurementUi();


  if (bar) {

    bar.style.width =
      "100%";

  }

  finalizeFullMeasurement();

}

      },
      SMAV_SIMPLE_TICK_MS
    );
}

  // =====================================================
  // VISTA SENCILLA DE MEDICIÓN
  // =====================================================

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
    var sample = { t: t, x: x, y: y, z: z };
    samples.push(sample);
    // Guardar también la muestra en la medición
// completa de 10 segundos.
if (isMeasurementCapturing) {

    if (measurementStartedAt === null) {
        measurementStartedAt = t;
    }

    var measurementElapsed =
        t - measurementStartedAt;

    if (
        measurementElapsed
        <= SIMPLE_MEASUREMENT_DURATION_MS
    ) {
        measurementSamples.push(sample);
    }
}
    var mag = Math.sqrt(x * x + y * y + z * z);
    scopeBuffer.push(mag);
    if (scopeBuffer.length > MAX_SCOPE_POINTS) scopeBuffer.shift();
    // Descartamos muestras fuera de la ventana.
    var cutoff = t - WINDOW_MS;
    while (samples.length && samples[0].t < cutoff) samples.shift();
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


  if (!res.ok) {
    return;
  }
  if (!running) {
    return;
  }
  updateReadout(
    res.data
  );

})
      .catch(function () {
        lastAnalyzeInFlight = false;
      });
  }

// =====================================================
// RESULTADOS VISUALES DE LA MEDICIÓN
// =====================================================

var currentMeasurementFolio = "";


function createMeasurementFolio() {

  var now =
    new Date();


  function pad(value) {

    return String(value)
      .padStart(
        2,
        "0"
      );

  }


  return (
    "SMAV-"
    + now.getFullYear()
    + pad(
        now.getMonth() + 1
      )
    + pad(
        now.getDate()
      )
    + "-"
    + pad(
        now.getHours()
      )
    + pad(
        now.getMinutes()
      )
    + pad(
        now.getSeconds()
      )
  );
}


function hideMeasurementResult() {

  var result =
    document.getElementById(
      "measurement-result"
    );


  if (result) {

    result.hidden =
      true;

  }


  for (
    var index = 1;
    index <= 4;
    index += 1
  ) {

    var state =
      document.getElementById(
        "measurement-result-state-"
        + index
      );


    if (state) {

      state.hidden =
        true;

    }

  }
}


function showMeasurementResult(
  stateNumber,
  data
) {

  var result =
    document.getElementById(
      "measurement-result"
    );


  if (!result) {

    return;

  }

  hideMeasurementResult();


  /*
   * Generamos un folio nuevo
   * para esta medición.
   */
  if (!currentMeasurementFolio) {

    currentMeasurementFolio =
      createMeasurementFolio();

  }


  var folio =
    document.getElementById(
      "measurement-result-folio"
    );


  if (folio) {

    folio.textContent =
      "Folio "
      + currentMeasurementFolio;

  }


  var inlineFolio =
    document.getElementById(
      "measurement-result-folio-inline-3"
    );


  if (inlineFolio) {

    inlineFolio.textContent =
      currentMeasurementFolio;

  }


  /*
   * Frecuencia para
   * resultados 3 y 4.
   */
  if (
    data
    &&
    typeof data.dominant_hz
      === "number"
  ) {

    var frequencyText =
      data.dominant_hz.toFixed(1)
      + " Hz";


    var frequency3 =
      document.getElementById(
        "measurement-result-frequency-3"
      );


    var frequency4 =
      document.getElementById(
        "measurement-result-frequency-4"
      );


    if (frequency3) {

      frequency3.textContent =
        frequencyText;

    }


    if (frequency4) {

      frequency4.textContent =
        frequencyText;

    }

  }


  var selectedState =
    document.getElementById(
      "measurement-result-state-"
      + stateNumber
    );


  if (!selectedState) {

    return;

  }


  result.hidden =
    false;

  selectedState.hidden =
    false;


  /*
   * Llevamos al usuario
   * al resultado.
   */
  window.setTimeout(
    function () {

      result.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });

    },
    150
  );
}

function finalizeFullMeasurement() {

  /*
   * Cerramos la captura completa.
   * Aquí obtenemos los 10 segundos.
   */
  var finalSamples =
    stopFullMeasurementCapture();


  /*
   * Detenemos sensor,
   * análisis en vivo y temporizadores.
   */
  if (running) {

    stop();

  }


  /*
   * No hubo suficientes datos.
   *
   * RESULTADO 1:
   * "No se obtuvo una lectura clara."
   */
  if (
    !finalSamples
    ||
    finalSamples.length < 16
  ) {

    smavSetSimpleError(
      "No se recibieron suficientes datos "
      + "del acelerómetro."
    );


    setStatus(
      "Medición insuficiente.",
      false
    );


    showMeasurementResult(
      1
    );


    return;
  }


  /*
   * Analizamos los 10 segundos
   * completos.
   */
  analyzeSampleSet(
    finalSamples
  )

    .then(
      function (data) {

        /*
         * Resultado definitivo.
         */
        updateReadout(
          data
        );


        smavSetSimpleFinished();


        setStatus(
          "Medición completada",
          false
        );


        /*
         * RESULTADO 3
         *
         * Frecuencia menor a 25 Hz.
         */
        if (
          data.dominant_hz < 25
        ) {

          showMeasurementResult(
            3,
            data
          );

        }

        /*
         * RESULTADO 4
         *
         * Frecuencia igual o mayor
         * a 25 Hz.
         */
        else {

          showMeasurementResult(
            4,
            data
          );

        }


        /*
         * El PDF continúa funcionando
         * exactamente como antes.
         */
        prepareMeasurementPdfForShare();

      }
    )

    .catch(
      function (error) {

        console.error(
          "[SMAV FINAL]",
          error
        );


        smavSetSimpleError(
          "No se pudo procesar la medición. "
          + "Intenta realizarla nuevamente."
        );


        setStatus(
          "No se pudo completar "
          + "el análisis final.",
          false
        );


        /*
         * Si el análisis no pudo
         * producir una lectura válida,
         * mostramos RESULTADO 1.
         */
        showMeasurementResult(
          1
        );

      }
    );
}

function analyzeSampleSet(
  sampleSet
) {

  if (
    !sampleSet
    ||
    sampleSet.length < 16
  ) {

    return Promise.reject(
      new Error(
        "No hay suficientes muestras "
        + "para realizar el análisis final."
      )
    );

  }


  var payload = {

    samples:
      sampleSet.map(
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


  return fetch(
    ANALYZE_URL,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body:
        JSON.stringify(
          payload
        ),
    }
  )

    .then(
      function (response) {

        return response
          .json()
          .then(
            function (data) {

              if (!response.ok) {

                throw new Error(
                  data.detail
                  ||
                  "No se pudo analizar "
                  + "la medición final."
                );

              }


              return data;

            }
          );

      }
    );

}

function updateReadout(d) {

  latestAnalysis = d;


  // Valor antiguo.
  // Aunque ahora queda oculto en Medición avanzada,
  // lo mantenemos para no romper la lógica existente.
  if (els.hz) {

    els.hz.textContent =
      d.dominant_hz.toFixed(1);

  }


  // NUEVO INDICADOR PRINCIPAL
 


  els.rpm.textContent =
    Math.round(
      d.rpm
    );


  els.fs.textContent =
    d.sample_rate_hz.toFixed(0)
    + " Hz";


  renderMeasurementUnit();


  drawSpectrum(
    d.spectrum,
    d.dominant_hz
  );


  els.pdf.disabled =
    false;
}

  // ---- Bucle de render ----
  function renderLoop() {
    if (!running) return;
    drawScope();
    requestAnimationFrame(renderLoop);
  }

function startCommon(label) {

  running = true;

  samples = [];

  scopeBuffer = [];

  latestAnalysis = null;

  preparedShareFile =
    null;
  
  currentMeasurementFolio =
  "";

hideMeasurementResult();  


  /*
   * Aquí comienza realmente
   * la captura completa de 10 segundos.
   */
  startFullMeasurementCapture();


  renderMeasurementUnit();


  els.start.disabled = true;

  els.pdf.disabled = true;

  if (els.sharePdf) {

    els.sharePdf.disabled =
      true;

    els.sharePdf.textContent =
      "Enviar PDF a INAHER";
  }

  els.stop.disabled = false;

  setStatus(
    label,
    true
  );


  analyzeTimer =
    setInterval(
      analyze,
      ANALYZE_EVERY_MS
    );


  requestAnimationFrame(
    renderLoop
  );


  /*
   * La interfaz visual se ejecuta aparte.
   * Si llegara a fallar, NO rompe
   * la medición del acelerómetro.
   */
  try {

    smavStartSimpleMeasurementUi();

  } catch (error) {

    console.error(
      "[SMAV UI] Error:",
      error
    );

  }
}

function startReal() {

  motionHandler =
    onMotion;


  window.addEventListener(
    "devicemotion",
    motionHandler,
    true
  );


  startCommon(
    "Midiendo (sensor)..."
  );


  /*
   * Si después de 2.5 segundos
   * no recibimos ninguna muestra,
   * avisamos al usuario.
   */
  setTimeout(
    function () {

      if (
        running
        &&
        samples.length === 0
      ) {

        setStatus(
          "Sin datos del acelerómetro. "
          + "Verifica los permisos del sensor.",
          false
        );


        smavSetSimpleError(
          "No estamos recibiendo datos del sensor. "
          + "Revisa los permisos de movimiento "
          + "del navegador."
        );

      }

    },
    2500
  );
}

function getMeasurementSamplesForReport() {

  /*
   * Si existe una medición completa,
   * usamos los 10 segundos.
   */
  if (
    completedMeasurementSamples.length
    >= 8
  ) {

    return completedMeasurementSamples;

  }


  /*
   * Fallback para mantener
   * compatibilidad con el flujo anterior.
   */
  return samples;

}

function hasValidMeasurementForReport(
  reportSamples
) {

  return (
    !!latestAnalysis
    &&
    !!reportSamples
    &&
    reportSamples.length >= 8
  );
}

function requestMeasurementPdfFile() {

  var reportSamples =
    getMeasurementSamplesForReport();


  if (
    !hasValidMeasurementForReport(
      reportSamples
    )
  ) {

    return Promise.reject(
      new Error(
        "Primero realiza una medición válida."
      )
    );

  }


  var csrfInput =
    document.querySelector(
      "#measurement-pdf-csrf "
      + "input[name='csrfmiddlewaretoken']"
    );


  if (!csrfInput) {

    return Promise.reject(
      new Error(
        "No se encontró el token de seguridad."
      )
    );

  }


  var pdfUrl =
    els.pdf.getAttribute(
      "data-pdf-url"
    );


  if (!pdfUrl) {

    return Promise.reject(
      new Error(
        "No se encontró la ruta para generar el PDF."
      )
    );

  }


  var payload = {

    measurement_unit:
      measurementUnit,

    samples:
      reportSamples.map(
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


  return fetch(
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

      body:
        JSON.stringify(
          payload
        ),
    }
  )

    .then(
      function (response) {

        if (!response.ok) {

          return response
            .json()
            .catch(
              function () {
                return {};
              }
            )
            .then(
              function (data) {

                throw new Error(
                  data.detail
                  ||
                  "No se pudo generar el PDF."
                );

              }
            );

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
          &&
          match[1]
        ) {

          filename =
            match[1];

        }


        return response
          .blob()
          .then(
            function (blob) {

              return new File(
                [blob],
                filename,
                {
                  type:
                    "application/pdf",
                }
              );

            }
          );

      }
    );
}

function prepareMeasurementPdfForShare() {

  preparedShareFile =
    null;


  var reportSamples =
    getMeasurementSamplesForReport();


  if (
    !hasValidMeasurementForReport(
      reportSamples
    )
  ) {

    if (els.sharePdf) {

      els.sharePdf.disabled =
        true;

    }

    return;
  }


  if (els.sharePdf) {

    els.sharePdf.disabled =
      true;

    els.sharePdf.textContent =
      "Preparando PDF...";

  }


  requestMeasurementPdfFile()

    .then(
      function (file) {

        preparedShareFile =
          file;


        if (els.sharePdf) {

          els.sharePdf.disabled =
            false;

          els.sharePdf.textContent =
            "Enviar a INAHER";

        }

      }
    )

    .catch(
      function (error) {

        console.error(
          "[SMAV PDF]",
          error
        );


        preparedShareFile =
          null;


        if (els.sharePdf) {

          els.sharePdf.disabled =
            false;

          els.sharePdf.textContent =
            "Enviar a INAHER";

        }

      }
    );
}

function downloadSharedPdfFile(
  file
) {

  var objectUrl =
    URL.createObjectURL(
      file
    );


  var link =
    document.createElement(
      "a"
    );


  link.href =
    objectUrl;

  link.download =
    file.name;


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
    1500
  );
}

function openInaherMailDraft() {

  var email =
    "ventas@inahermex.com";


  var subject =
    "Reporte de medición vibratoria "
    + "SMAV INAHER";


  var body =
    "Hola INAHER,%0D%0A%0D%0A"
    + "Adjunto mi reporte de medición "
    + "vibratoria generado desde SMAV.%0D%0A%0D%0A"
    + "El archivo PDF acaba de descargarse "
    + "en mi dispositivo.%0D%0A";


  var mailto =
    "mailto:"
    + email
    + "?subject="
    + encodeURIComponent(
        subject
      )
    + "&body="
    + body;


  window.location.href =
    mailto;
}

function shareMeasurementPdf() {

  var reportSamples =
    getMeasurementSamplesForReport();


  if (
    !hasValidMeasurementForReport(
      reportSamples
    )
  ) {

    window.alert(
      "Primero realiza una medición válida."
    );

    return;
  }


  /*
   * Si todavía no está preparado,
   * lo generamos.
   *
   * Después el usuario deberá
   * pulsar nuevamente.
   */
  if (!preparedShareFile) {

    if (els.sharePdf) {

      els.sharePdf.disabled =
        true;

      els.sharePdf.textContent =
        "Preparando PDF...";

    }


    requestMeasurementPdfFile()

      .then(function (file) {

        preparedShareFile =
          file;


        if (els.sharePdf) {

          els.sharePdf.disabled =
            false;

          els.sharePdf.textContent =
            "Compartir PDF";

        }


        window.alert(
          "El PDF está listo. "
          + "Pulsa nuevamente para compartirlo."
        );

      })

      .catch(function (error) {

        if (els.sharePdf) {

          els.sharePdf.disabled =
            false;

          els.sharePdf.textContent =
            "Enviar a INAHER";

        }


        window.alert(
          error.message
          || "No se pudo preparar el PDF."
        );

      });


    return;
  }


  /*
   * Web Share API con archivos.
   *
   * iPhone / Android y algunos
   * navegadores de escritorio.
   */
  var shareData = {

    title:
      "Reporte de medición "
      + "vibratoria SMAV INAHER",

    text:
      "Enviar este reporte a "
      + "ventas@inahermex.com",

    files: [
      preparedShareFile,
    ],
  };


  var canShareFiles =
    (
      navigator.share
      && navigator.canShare
      && navigator.canShare(
        {
          files: [
            preparedShareFile,
          ],
        }
      )
    );


  if (canShareFiles) {

    navigator.share(
      shareData
    )

      .catch(function (error) {

        /*
         * El usuario simplemente cerró
         * el menú de compartir.
         */
        if (
          error
          && error.name ===
            "AbortError"
        ) {
          return;
        }


        console.error(
          "[SMAV SHARE]",
          error
        );


        window.alert(
          "No se pudo abrir "
          + "el menú de compartir."
        );

      });


    return;
  }


  /*
   * FALLBACK PARA COMPUTADORAS
   * SIN WEB SHARE DE ARCHIVOS.
   */
  downloadSharedPdfFile(
    preparedShareFile
  );


  window.setTimeout(
    function () {

      openInaherMailDraft();

    },
    450
  );
}

function downloadMeasurementPdf() {

  var reportSamples =
    getMeasurementSamplesForReport();


  if (
    !hasValidMeasurementForReport(
      reportSamples
  )
  ) {

    window.alert(
      "Primero realiza una medición válida."
    );

    return;
}


  var originalText =
    els.pdf.textContent;


  els.pdf.disabled =
    true;

  els.pdf.textContent =
    "Generando...";


  requestMeasurementPdfFile()

    .then(
      function (file) {

        downloadSharedPdfFile(
          file
        );

      }
    )

    .catch(
      function (error) {

        console.error(
          "[SMAV PDF]",
          error
        );


        window.alert(
          error.message
          ||
          "No se pudo generar el PDF."
        );

      }
    )

    .finally(
      function () {

        els.pdf.textContent =
          originalText;


        els.pdf.disabled =
          (
            !latestAnalysis
            ||
            getMeasurementSamplesForReport()
              .length < 8
          );

      }
    );
}

function stop() {

  if (isMeasurementCapturing) {

  cancelFullMeasurementCapture();

}

  running = false;

  if (motionHandler) {

    window.removeEventListener(
      "devicemotion",
      motionHandler,
      true
    );

    motionHandler = null;
  }


  if (analyzeTimer) {

    clearInterval(
      analyzeTimer
    );

    analyzeTimer = null;
  }


  els.start.disabled = false;


 els.pdf.disabled =
  !latestAnalysis
  ||
  getMeasurementSamplesForReport()
    .length < 8;


  els.stop.disabled =
    true;


  setStatus(
    "Detenido",
    false
  );
  /*
  * Detenemos solamente la interfaz.
  */
  smavStopSimpleMeasurementUi();
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

function handleStartMeasurement() {

  if (running) {
    return;
  }

  requestMotionPermission()
    .then(function (granted) {

      if (!granted) {

        setStatus(
          "Permiso de movimiento denegado.",
          false
        );

        smavSetSimpleError(
          "Debes permitir el acceso al movimiento "
          + "del dispositivo para realizar la medición."
        );

        return;
      }

      startReal();

    })
    
  .catch(
    function (error) {

      console.error(
        "[SMAV SENSOR]",
        error
      );


      setStatus(
        "No se pudo acceder al acelerómetro.",
        false
      );


      smavSetSimpleError(
        "El navegador no pudo acceder "
        + "al sensor de movimiento."
      );

    }
  );
}


els.start.addEventListener(
  "click",
  handleStartMeasurement
);

// =====================================================
// BOTONES DE LA MEDICIÓN SENCILLA
// =====================================================

els.pdf.addEventListener(
  "click",
  function () {
    downloadMeasurementPdf();
  }
);

if (els.sharePdf) {

  els.sharePdf.addEventListener(
    "click",
    function () {

      shareMeasurementPdf();

    }
  );

}

  els.stop.addEventListener(
    "click",
    function () {

      stop();

    }
  );

  // Estado inicial de los lienzos.
setMeasurementUnit("acceleration");
drawScope();
drawSpectrum([], 0);

  
 
  if (
    els.advancedPanel
    &&
    els.simpleCard
  ) {

    els.advancedPanel.addEventListener(
      "toggle",
      function () {

        if (els.advancedPanel.open) {


          els.simpleCard.hidden =
            true;

        } else {


          els.simpleCard.hidden =
            false;

        }

      }
    );
  } 

 
})();