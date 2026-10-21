// Medicion de vibraciones en el navegador (Android / iOS).
// Captura muestras del acelerometro con la API DeviceMotion.
// La señal se envía en UN SOLO POST al terminar los 10 s (Sección 7.1 del Libro Maestro).
// No se envían peticiones intermedias al servidor durante la captura.

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
  // Sección 7.1: Sin POSTs intermedios. El análisis se realiza en un único
  // POST al finalizar la captura completa de 10 s.
  var WINDOW_MS = 3000; // ventana del osciloscopio en vivo (sin servidor)
  var MAX_SCOPE_POINTS = 300;
  var SIMPLE_MEASUREMENT_DURATION_MS = 10000;
  // Mínimo de muestras requeridas antes de enviar al servidor (Sección 7.1)
  var MIN_SAMPLES_TO_SEND = 400;
  // Frecuencia en vivo calculada en el celular (sin servidor), cada 500 ms
  var LIVE_TICK_MS = 500;

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
  var motionHandler = null;
  var measurementUnit = "acceleration";
  var latestAnalysis = null;

  // wakeLock: evita que la pantalla se apague durante la captura (Sección 7.1)
  var wakeLockSentinel = null;

  // Timer del contador en vivo (calculado en JS, sin peticiones al servidor)
  var liveReadoutTimer = null;

  // Bandera: indica si el sensor incluye gravedad estática (fallback en iOS)
  var gravityIncluded = false;

  // RPM de placa opcionales ingresadas por el usuario
  function getRpmPlaca() {
    var input = document.getElementById("rpm-placa-input");
    if (!input) return null;
    var val = parseFloat(input.value);
    return (isFinite(val) && val > 0) ? val : null;
  }

  // Adquiere o libera el wakeLock de pantalla
  function acquireWakeLock() {
    if (!("wakeLock" in navigator)) return;
    navigator.wakeLock.request("screen").then(function (lock) {
      wakeLockSentinel = lock;
    }).catch(function () {
      // El wakeLock es opcional; si falla, la medición continúa igual
    });
  }

  function releaseWakeLock() {
    if (wakeLockSentinel) {
      wakeLockSentinel.release().catch(function () {});
      wakeLockSentinel = null;
    }
  }

  // ---- Micrófono (Sección 7.5): solo aporta frecuencia ----
  // Graba los primeros 5 s con el celular apoyado en el chasis y se envía
  // en el mismo POST final. Sin permiso de micrófono la medición sigue igual.
  var ACOUSTIC_DURATION_S = 5;
  var ACOUSTIC_MIN_S = 2;
  var acoustic = null;
  var lastAcousticPayload = null;

  // El AudioContext se crea dentro del clic: iOS lo exige para poder sonar/grabar
  function createAudioContextInGesture() {
    var AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (
      !AudioCtx
      || !navigator.mediaDevices
      || typeof navigator.mediaDevices.getUserMedia !== "function"
    ) {
      return null;
    }
    try {
      var ctx = new AudioCtx();
      if (ctx.resume) ctx.resume().catch(function () {});
      return ctx;
    } catch (error) {
      return null;
    }
  }

  // Pide el micrófono antes de medir, para que el aviso de permiso
  // no aparezca a mitad de la medición y mueva el celular.
  function requestMicrophone(ctx) {
    if (!ctx) return Promise.resolve(null);
    return navigator.mediaDevices
      .getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
        video: false,
      })
      .catch(function (error) {
        console.warn("[SMAV MIC] Sin micrófono:", error);
        return null;
      });
  }

  function startAcousticCapture(ctx, stream) {
    stopAcousticCapture();
    acoustic = { ctx: ctx, stream: stream, chunks: [], length: 0, rate: 0 };
    if (!ctx || !stream) return;

    acoustic.rate = ctx.sampleRate;
    var target = Math.round(ctx.sampleRate * ACOUSTIC_DURATION_S);

    // ScriptProcessor: funciona en Safari, Chrome y Firefox sin módulos extra
    var source = ctx.createMediaStreamSource(stream);
    var processor = ctx.createScriptProcessor(4096, 1, 1);
    var mute = ctx.createGain();
    mute.gain.value = 0;

    processor.onaudioprocess = function (event) {
      if (!acoustic || acoustic.length >= target) return;
      var data = event.inputBuffer.getChannelData(0);
      var take = Math.min(data.length, target - acoustic.length);
      acoustic.chunks.push(new Float32Array(data.subarray(0, take)));
      acoustic.length += take;
      if (acoustic.length >= target) stopAcousticCapture();
    };

    source.connect(processor);
    processor.connect(mute);
    mute.connect(ctx.destination);

    acoustic.source = source;
    acoustic.processor = processor;
    acoustic.mute = mute;
  }

  // Apaga el micrófono; conserva lo grabado para el envío
  function stopAcousticCapture() {
    if (!acoustic) return;
    try {
      if (acoustic.processor) {
        acoustic.processor.onaudioprocess = null;
        acoustic.processor.disconnect();
      }
      if (acoustic.source) acoustic.source.disconnect();
      if (acoustic.mute) acoustic.mute.disconnect();
    } catch (error) {
      // ya desconectado
    }
    if (acoustic.stream) {
      acoustic.stream.getTracks().forEach(function (track) { track.stop(); });
      acoustic.stream = null;
    }
    if (acoustic.ctx && acoustic.ctx.state !== "closed" && acoustic.ctx.close) {
      acoustic.ctx.close().catch(function () {});
    }
    acoustic.processor = null;
    acoustic.source = null;
    acoustic.mute = null;
  }

  // PCM 16 bits little-endian en base64, como lo espera el servidor
  function buildAcousticPayload() {
    if (!acoustic || !acoustic.rate || acoustic.length < acoustic.rate * ACOUSTIC_MIN_S) {
      return null;
    }

    var pcm = new Int16Array(acoustic.length);
    var offset = 0;
    acoustic.chunks.forEach(function (chunk) {
      for (var i = 0; i < chunk.length; i++) {
        var s = Math.max(-1, Math.min(1, chunk[i]));
        pcm[offset++] = s < 0 ? s * 32768 : s * 32767;
      }
    });

    var bytes = new Uint8Array(pcm.buffer);
    var binary = "";
    for (var j = 0; j < bytes.length; j += 0x8000) {
      binary += String.fromCharCode.apply(null, bytes.subarray(j, j + 0x8000));
    }

    return {
      audio_pcm16: btoa(binary),
      audio_sample_rate: Math.round(acoustic.rate),
    };
  }

  // Frecuencia en vivo calculada en el celular con los últimos 3 s.
  // Solo anima el contador; el resultado final lo calcula el servidor
  // con las muestras completas (sin POSTs durante la captura, decisión 11).
  var LIVE_MIN_HZ = 2;
  var LIVE_STEP_HZ = 0.25;

  function computeLiveFrequency(sampleSet) {
    var n = sampleSet.length;
    if (n < 30) return null;

    var spanS = (sampleSet[n - 1].t - sampleSet[0].t) / 1000;
    if (spanS <= 0) return null;
    var maxHz = 0.45 * ((n - 1) / spanS);

    // Eje de mayor varianza, sin la media (gravedad y offset)
    var axes = ["x", "y", "z"];
    var best = null;
    var bestVar = -1;
    axes.forEach(function (axis) {
      var mean = 0;
      sampleSet.forEach(function (s) { mean += s[axis]; });
      mean /= n;
      var v = 0;
      sampleSet.forEach(function (s) { v += (s[axis] - mean) * (s[axis] - mean); });
      if (v > bestVar) {
        bestVar = v;
        best = sampleSet.map(function (s) { return s[axis] - mean; });
      }
    });
    if (bestVar <= 0) return null;

    // DFT directa con los tiempos reales de cada muestra
    var t0 = sampleSet[0].t;
    var peakHz = null;
    var peakPower = 0;
    for (var f = LIVE_MIN_HZ; f <= maxHz; f += LIVE_STEP_HZ) {
      var re = 0;
      var im = 0;
      for (var i = 0; i < n; i++) {
        var phase = 2 * Math.PI * f * (sampleSet[i].t - t0) / 1000;
        re += best[i] * Math.cos(phase);
        im -= best[i] * Math.sin(phase);
      }
      var power = re * re + im * im;
      if (power > peakPower) {
        peakPower = power;
        peakHz = f;
      }
    }
    return peakHz;
  }

  function updateLiveReadout() {
    if (!els.hz) return;
    var hz = computeLiveFrequency(samples);
    els.hz.textContent = hz === null ? "0.0" : hz.toFixed(1);
  }

  function startLiveReadout() {
    stopLiveReadout();
    if (els.hz) els.hz.textContent = "0.0";
    liveReadoutTimer = setInterval(updateLiveReadout, LIVE_TICK_MS);
  }

  function stopLiveReadout() {
    if (liveReadoutTimer !== null) {
      clearInterval(liveReadoutTimer);
      liveReadoutTimer = null;
    }
  }

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

  setRingProgress(0);
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

  setRingProgress(1);
}


// Anillo de progreso de los 10 s (circunferencia 2·π·64 ≈ 402)
var RING_LENGTH = 402;

function setRingProgress(fraction) {

  var ring =
    document.getElementById(
      "measurement-simple-ring-progress"
    );

  if (!ring) {
    return;
  }

  // Con unidad "px": Safari ignora números sin unidad en el estilo
  ring.style.strokeDashoffset =
    (RING_LENGTH * (1 - Math.max(0, Math.min(1, fraction)))) + "px";
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

  setRingProgress(0);


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

        setRingProgress(progress);


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
    // Detectar si estamos usando la señal con gravedad incluida (fallback en iOS)
    if (src === incGravity && (!a || a.x === null)) {
      gravityIncluded = true;
    }
    // Tiempo real del evento del sensor (Sección 7.1); el servidor remuestrea.
    // Solo se usa si está en la misma base que performance.now(): algunos
    // navegadores (Safari antiguo) lo dan en otra base o en cero, y mezclar
    // relojes vacía la ventana de muestras y congela el contador.
    var t = now();
    var ts = event.timeStamp;
    if (typeof ts === "number" && ts > 0 && Math.abs(t - ts) < 1000) {
      t = ts;
    }
    pushSample(src.x || 0, src.y || 0, src.z || 0, t);
  }

  function pushSample(x, y, z, t) {
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

    // Sin frecuencia clara no hay etiqueta de pico.
    if (typeof dominantHz !== "number") return;

    // Etiqueta del pico.
    c.fillStyle = COLORS.muted;
    c.font = "12px Montserrat, sans-serif";
    c.textAlign = "center";
    c.fillText(dominantHz.toFixed(1) + " Hz", w / 2, h - 4);
  }

// =====================================================
// RESULTADOS VISUALES DE LA MEDICIÓN
// =====================================================

var currentMeasurementFolio = "";

var currentMeasurementToken = "";

function createMeasurementToken() {

  if (
    window.crypto
    &&
    typeof window.crypto.randomUUID
      === "function"
  ) {

    return window.crypto.randomUUID();

  }


  return (
    "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
  ).replace(
    /[xy]/g,
    function (character) {

      var random =
        Math.random() * 16 | 0;

      var value =
        character === "x"
          ? random
          : (
              random & 0x3
            ) | 0x8;

      return value.toString(16);

    }
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


function updateMeasurementFolioDisplay() {

  var folio =
    document.getElementById(
      "measurement-result-folio"
    );


  if (folio) {

    if (currentMeasurementFolio) {

      folio.textContent =
        "Folio "
        + currentMeasurementFolio;

    } else {

      folio.textContent =
        "Genera el PDF para obtener tu folio";

    }

  }


  var inlineFolio =
    document.getElementById(
      "measurement-result-folio-inline-3"
    );


  if (inlineFolio) {

    inlineFolio.textContent =
      currentMeasurementFolio
      || "pendiente";

  }

}

// =====================================================
// CONTENIDO DE LAS TARJETAS DE RESULTADO
// =====================================================

var RESULT_LEVELS = {
  low: { label: "BAJA", word: "baja", cls: "is-low" },
  medium: { label: "MEDIA", word: "media", cls: "is-medium" },
  high: { label: "ALTA", word: "alta", cls: "is-high" },
};


// Miles con coma: 2502 -> "2,502"
function formatThousands(value) {

  return String(
    Math.round(value)
  ).replace(
    /\B(?=(\d{3})+(?!\d))/g,
    ","
  );
}


function setResultText(id, text) {

  var element =
    document.getElementById(id);

  if (!element) {
    return null;
  }

  element.textContent =
    text || "";

  element.hidden =
    !text;

  return element;
}


function fillResultCards(data) {

  var vibration =
    document.getElementById(
      "measurement-result-vibration"
    );

  // Sin datos (la medición falló): solo el aviso de la tarjeta 1
  if (!data) {

    if (vibration) {
      vibration.hidden = true;
    }

    setResultText(
      "measurement-result-title-1",
      "No se obtuvo una lectura clara."
    );

    setResultText(
      "measurement-result-text-1",
      "Intenta de nuevo apoyando mejor el teléfono. "
      + "Si sigue igual, continúa con la selección de tu "
      + "soporte con el peso de tu máquina o equipo."
    );

    return;
  }


  // ---- Vibración medida (todas las tarjetas) ----
  var level =
    RESULT_LEVELS[data.level]
    || RESULT_LEVELS.low;

  var levelChip =
    document.getElementById(
      "measurement-result-level"
    );

  if (levelChip) {

    levelChip.textContent =
      "VIBRACIÓN " + level.label;

    levelChip.className =
      "measurement-result-level " + level.cls;
  }

  setResultText(
    "measurement-result-rms",
    data.rms_ms2.toFixed(2) + " m/s²"
  );

  setResultText(
    "measurement-result-peak",
    data.peak_ms2.toFixed(2) + " m/s²"
  );

  setResultText(
    "measurement-result-impacts",
    data.impacts
      ? (
        "El pico es "
        + Math.round(data.crest)
        + " veces el RMS: hubo golpes o se movió el teléfono. "
        + "Repite la medición para confirmar."
      )
      : ""
  );

  if (vibration) {
    vibration.hidden = false;
  }


  // ---- Frecuencia ----
  var hasHz =
    typeof data.dominant_hz === "number";

  var frequencyText =
    hasHz
      ? (
        data.dominant_hz.toFixed(1)
        + " Hz · "
        + formatThousands(data.dominant_rpm)
        + " rpm"
      )
      : "";

  ["2", "3", "4"].forEach(function (n) {
    setResultText(
      "measurement-result-frequency-" + n,
      frequencyText
    );
  });

  var limitHz =
    Math.floor(data.f_max_hz || 0);


  // Tarjeta 1: no hubo frecuencia clara, pero la vibración sí se midió
  setResultText(
    "measurement-result-title-1",
    data.frequency_status === "not_found"
      ? "No se detectó la frecuencia de placa."
      : "No se detectó una frecuencia clara."
  );

  setResultText(
    "measurement-result-text-1",
    "La vibración sí se midió (arriba). Este teléfono solo "
    + "detecta frecuencias hasta "
    + limitHz
    + " Hz ("
    + formatThousands(limitHz * 60)
    + " rpm). Repite apoyando mejor el teléfono o continúa "
    + "la selección con el peso de tu máquina."
  );


  // Tarjeta 2: cerca del límite del teléfono
  setResultText(
    "measurement-result-text-2",
    "Este teléfono detecta hasta "
    + limitHz
    + " Hz. Tómala con reserva y, si puedes, repite la medición."
  );


  // Tarjetas 3 y 4: el sello depende de si hubo golpes
  ["3", "4"].forEach(function (n) {

    var quality =
      document.getElementById(
        "measurement-result-quality-" + n
      );

    if (!quality) {
      return;
    }

    quality.textContent =
      data.impacts
        ? "⚠ Hubo golpes durante la medición"
        : (
          n === "4"
            ? "✓ Frecuencia confirmada"
            : "✓ Señal estable y clara"
        );

    quality.classList.toggle(
      "is-warning",
      !!data.impacts
    );
  });


  // Tarjeta 3: aviso de posible reflejo cerca del límite
  var reflectionNote = "";

  if (
    hasHz
    && data.frequency_status === "clear"
    && data.dominant_hz > 0.3 * data.sample_rate_hz
  ) {
    reflectionNote =
      "Podría ser un reflejo de "
      + Math.abs(data.dominant_hz - data.sample_rate_hz).toFixed(1)
      + " Hz por el límite del teléfono.";
  }

  setResultText(
    "measurement-result-note-3",
    reflectionNote
  );

  // Aviso de frecuencia baja solo cuando aplica
  var lowFrequency =
    document.getElementById(
      "measurement-result-low-frequency"
    );

  if (lowFrequency) {
    lowFrequency.hidden =
      !(hasHz && data.dominant_hz < 25);
  }


  // Tarjeta 4: por qué está confirmada (sonido o placa)
  var confirmation =
    data.frequency_message || "";

  var cut =
    confirmation.indexOf(". ");

  // El mensaje del alias empieza repitiendo "X Hz ≈ Y rpm."
  if (
    data.frequency_status === "aliased_confirmed"
    && cut >= 0
  ) {
    confirmation =
      confirmation.slice(cut + 2);
  }

  setResultText(
    "measurement-result-note-4",
    confirmation
  );
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


updateMeasurementFolioDisplay();

  fillResultCards(
    data
  );


  // Sección 7.5: lo que dijo el micrófono
  var acousticLine =
    document.getElementById(
      "measurement-result-acoustic"
    );

  if (acousticLine) {

    var acousticText = "";

    if (data && data.acoustic_used) {

      if (typeof data.acoustic_hz !== "number") {

        acousticText =
          "Micrófono: no se identificó la frecuencia por sonido.";

      } else if (data.acoustic_confidence === "high") {

        // La tarjeta 4 ya explica que el sonido lo confirma
        acousticText = "";

      } else {

        acousticText =
          data.frequency_note
          || (
            "El sonido marca "
            + data.acoustic_hz.toFixed(1)
            + " Hz, pero el movimiento no lo confirma."
          );

      }

    }

    acousticLine.textContent =
      acousticText;

    acousticLine.hidden =
      !acousticText;

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

  // Audio de los primeros 5 s (null si no hubo micrófono).
  // Un fallo del micrófono nunca bloquea la medición.
  try {

    stopAcousticCapture();

    lastAcousticPayload =
      buildAcousticPayload();

  } catch (error) {

    console.warn("[SMAV MIC]", error);

    lastAcousticPayload = null;

  }


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
   *
   * Sección 7.1: mínimo MIN_SAMPLES_TO_SEND (400) muestras en 10 s.
   * Con 60 Hz el celular genera ~600 muestras; si solo llegaron <400
   * hay un problema de sensor o apoyo.
   */
  if (
    !finalSamples
    ||
    finalSamples.length < MIN_SAMPLES_TO_SEND
  ) {

    smavSetSimpleError(
      finalSamples && finalSamples.length < MIN_SAMPLES_TO_SEND && finalSamples.length >= 16
        ? "Se recibieron pocas muestras del sensor ("
          + finalSamples.length + "). "
          + "Apoya mejor el teléfono sobre la máquina e intenta de nuevo."
        : "No se recibieron suficientes datos "
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
         * Selección del estado visual usando frequency_status
         * del nuevo motor DSP (Sección 7.6 del Libro Maestro).
         *
         * RESULTADO 1: señal no clara / sin frecuencia detectada
         * RESULTADO 2: frecuencia cerca del límite físico del sensor
         * RESULTADO 3: frecuencia confiable y clara
         * RESULTADO 4: frecuencia confirmada con datos de placa
         */
        var status = data.frequency_status;

        if (
          status === "unclear"
          || data.dominant_hz === null
          || data.dominant_hz === undefined
        ) {
          // Sin frecuencia clara
          showMeasurementResult(1, data);

        } else if (status === "near_limit") {
          // Cerca del límite físico (0.40*fs – 0.45*fs)
          showMeasurementResult(2, data);

        } else if (
          status === "aliased_confirmed"
          || status === "confirmed"
        ) {
          // Frecuencia resuelta con RPM de placa
          showMeasurementResult(4, data);

        } else {
          // "clear" o cualquier otro: frecuencia confiable
          showMeasurementResult(3, data);
        }


        /*
         * El PDF continúa funcionando
         * exactamente como antes.
         */
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

  // Agregar campos opcionales conforme a la Sección 7.1 del Libro Maestro
  var rpmPlaca = getRpmPlaca();
  if (rpmPlaca !== null) {
    payload.rpm_placa = rpmPlaca;
  }
  payload.gravity_included = gravityIncluded;
  payload.user_agent = navigator.userAgent || "";

  // Sección 7.5: el audio va en el mismo POST (sin envíos intermedios)
  if (lastAcousticPayload) {
    payload.audio_pcm16 = lastAcousticPayload.audio_pcm16;
    payload.audio_sample_rate = lastAcousticPayload.audio_sample_rate;
  }

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
  // dominant_hz es null cuando la frecuencia no es clara (Sección 7.2)
  if (els.hz) {

    els.hz.textContent =
      typeof d.dominant_hz === "number"
        ? d.dominant_hz.toFixed(1)
        : "—";

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

  
  currentMeasurementFolio =
  "";

    currentMeasurementToken =
      createMeasurementToken();

  updateMeasurementFolioDisplay();

hideMeasurementResult();  


  /*
   * Aquí comienza realmente
   * la captura completa de 10 segundos.
   */
  startFullMeasurementCapture();


  renderMeasurementUnit();


  els.start.disabled = true;

  els.pdf.disabled = true;


  els.stop.disabled = false;

  setStatus(
    label,
    true
  );


  // Sección 7.1: sin POSTs durante la captura; pantalla encendida
  // y frecuencia local cada 500 ms en el contador.
  gravityIncluded = false;

  lastAcousticPayload = null;

  acquireWakeLock();

  startLiveReadout();


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

  measurement_token:
    currentMeasurementToken,

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

  // Los mismos datos que se mandaron a /api/analyze/ (decisión 10)
  rpm_placa:
    latestAnalysis
      ? latestAnalysis.rpm_placa
      : null,

  gravity_included:
    gravityIncluded,

  user_agent:
    navigator.userAgent || "",

  // Mismo audio que en pantalla para que el PDF dé el mismo número
  audio_pcm16:
    lastAcousticPayload
      ? lastAcousticPayload.audio_pcm16
      : null,

  audio_sample_rate:
    lastAcousticPayload
      ? lastAcousticPayload.audio_sample_rate
      : null,

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


        var folio =
          response.headers.get(
            "X-SMAV-Folio"
          )
          || "";
        
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

              return {
  file:
    new File(
      [blob],
      filename,
      {
        type:
          "application/pdf",
      }
    ),

              folio:
              folio,
            };

            }
          );

      }
    );
}



function downloadPdfFile(
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
    function (result) {

      if (result.folio) {

        currentMeasurementFolio =
          result.folio;

        updateMeasurementFolioDisplay();

      }


      downloadPdfFile(
        result.file
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


  stopLiveReadout();

  stopAcousticCapture();

  releaseWakeLock();


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

// Evita dos arranques si tocan el botón dos veces mientras se
// piden los permisos (cada muestra se guardaría doble)
var isStartingMeasurement = false;

function handleStartMeasurement() {

  if (running || isStartingMeasurement) {
    return;
  }

  isStartingMeasurement = true;

  if (els.start) {
    els.start.disabled = true;
  }

  // Dentro del clic: iOS solo deja grabar audio si se crea aquí
  var audioCtx =
    createAudioContextInGesture();

  requestMotionPermission()
    .then(function (granted) {

      if (!granted) {

        if (audioCtx && audioCtx.close) {
          audioCtx.close().catch(function () {});
        }

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

      // Micrófono opcional (Sección 7.5): si no hay permiso, se mide igual
      return requestMicrophone(audioCtx)
        .then(function (stream) {

          if (!stream && audioCtx && audioCtx.close) {
            audioCtx.close().catch(function () {});
          }

          startReal();

          startAcousticCapture(
            stream ? audioCtx : null,
            stream
          );

        });

    })

  .then(
    function () {

      isStartingMeasurement = false;

      // Si no arrancó (permiso negado), el botón vuelve a quedar activo
      if (!running && els.start) {
        els.start.disabled = false;
      }

    }
  )
    
  .catch(
    function (error) {

      console.error(
        "[SMAV SENSOR]",
        error
      );

      isStartingMeasurement = false;

      if (!running && els.start) {
        els.start.disabled = false;
      }


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

  
})();