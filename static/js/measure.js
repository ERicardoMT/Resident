// Medicion de vibraciones en el navegador (Android / iOS).
// Captura muestras del acelerometro con la API DeviceMotion y las envia a la
// API REST de Django (POST /api/analyze/) para el analisis FFT en el servidor.

(function () {
  "use strict";

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

  var els = {
    hz: document.getElementById("hz-value"),
    caption: document.getElementById("hz-caption"),
    rpm: document.getElementById("stat-rpm"),
    fs: document.getElementById("stat-fs"),
    rms: document.getElementById("stat-rms"),
    peak: document.getElementById("stat-peak"),
    dot: document.getElementById("status-dot"),
    statusText: document.getElementById("status-text"),
    start: document.getElementById("btn-start"),
    stop: document.getElementById("btn-stop"),
    demo: document.getElementById("btn-demo"),
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
    c.strokeStyle = "#d3d7e0";
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

    c.strokeStyle = "#d81f2a";
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
      c.fillStyle = isPeak ? "#d81f2a" : "#14204e";
      c.globalAlpha = isPeak ? 1 : 0.55;
      c.fillRect(x, y, barW, barH);
    }
    c.globalAlpha = 1;

    // Etiqueta del pico.
    c.fillStyle = "#6b7280";
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
    els.hz.textContent = d.dominant_hz.toFixed(1);
    els.rpm.textContent = Math.round(d.rpm);
    els.fs.textContent = d.sample_rate_hz.toFixed(0) + " Hz";
    els.rms.textContent = d.rms_g.toFixed(3) + " g";
    els.peak.textContent = d.peak_g.toFixed(3) + " g";
    drawSpectrum(d.spectrum, d.dominant_hz);
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
    els.start.disabled = true;
    els.demo.disabled = true;
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
        setStatus("Sin datos del acelerometro. Prueba el modo demostracion.", false);
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
    els.demo.disabled = false;
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

  els.demo.addEventListener("click", function () {
    startDemo();
  });

  els.stop.addEventListener("click", stop);

  // Estado inicial de los lienzos.
  drawScope();
  drawSpectrum([], 0);
})();
