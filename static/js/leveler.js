(function () {
  "use strict";

  var elements = {
    card: document.getElementById("leveler-card"),
    visual: document.getElementById("leveler-visual"),

    mode: document.getElementById("level-mode"),
    modeDescription: document.getElementById(
      "level-mode-description"
    ),

    dot: document.getElementById("level-dot"),
    status: document.getElementById("level-status"),
    stability: document.getElementById("level-stability"),

    surface: document.getElementById("level-surface"),
    tube: document.getElementById("level-tube"),
    bubble: document.getElementById("level-bubble"),
    tubeBubble: document.getElementById("level-tube-bubble"),

    surfaceReadings: document.getElementById(
      "level-surface-readings"
    ),
    edgeReading: document.getElementById(
      "level-edge-reading"
    ),

    x: document.getElementById("level-x"),
    y: document.getElementById("level-y"),
    total: document.getElementById("level-total"),

    angle: document.getElementById("level-angle"),
    angleLabel: document.getElementById(
      "level-angle-label"
    ),
    direction: document.getElementById("level-direction"),

    tolerance: document.getElementById("level-tolerance"),
    toleranceValue: document.getElementById(
      "level-tolerance-value"
    ),

    start: document.getElementById("btn-level-start"),
    stop: document.getElementById("btn-level-stop"),
    zero: document.getElementById("btn-level-zero"),
    reset: document.getElementById("btn-level-reset"),

    message: document.getElementById("level-message"),
    calibrationState: document.getElementById(
      "level-calibration-state"
    ),
  };

  var STORAGE_KEY = "smav_auto_leveler_v1";

  var MODE_INFORMATION = {
    surface: {
      title: "Acostado · dos ejes",
      description:
        "El teléfono está apoyado con la pantalla paralela a la superficie.",
      angleLabel: "Inclinación total",
    },

    horizontal: {
      title: "Horizontal · borde largo",
      description:
        "El teléfono está apoyado sobre uno de sus bordes largos.",
      angleLabel: "Nivel horizontal",
    },

    vertical: {
      title: "Vertical · borde corto",
      description:
        "El teléfono está apoyado sobre su borde corto y mide la vertical.",
      angleLabel: "Desviación vertical",
    },
  };

  var DEFAULT_OFFSETS = {
    surface: {
      x: 0,
      y: 0,
      active: false,
    },

    horizontal: {
      angle: 0,
      active: false,
    },

    vertical: {
      angle: 0,
      active: false,
    },
  };

  var state = {
    running: false,
    hasReading: false,

    gravity: null,

    mode: null,
    modeCandidate: null,
    modeCandidateCount: 0,

    raw: null,
    corrected: null,

    tolerance: 0.5,
    offsets: JSON.parse(JSON.stringify(DEFAULT_OFFSETS)),

    samples: [],
    stableLevelCounter: 0,
    vibrationSent: false,

    sensorTimeout: null,
  };

  /*
   * Un valor bajo produce una lectura más suave.
   * Un valor alto responde más rápido, pero aumenta el ruido.
   */
  var FILTER_ALPHA = 0.12;

  var MODE_CONFIRMATION_SAMPLES = 10;
  var MAX_STABILITY_SAMPLES = 30;
  var MIN_STABILITY_SAMPLES = 18;
  var STABILITY_LIMIT = 0.16;

  function clamp(value, minimum, maximum) {
    return Math.min(Math.max(value, minimum), maximum);
  }

  function finiteNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function toDegrees(radians) {
    return radians * (180 / Math.PI);
  }

  function copyDefaultOffsets() {
    return JSON.parse(JSON.stringify(DEFAULT_OFFSETS));
  }

  function loadSettings() {
    try {
      var stored = window.localStorage.getItem(STORAGE_KEY);

      if (!stored) {
        return;
      }

      var parsed = JSON.parse(stored);

      if (finiteNumber(parsed.tolerance)) {
        state.tolerance = clamp(parsed.tolerance, 0.2, 2);
      }

      if (!parsed.offsets) {
        return;
      }

      ["surface", "horizontal", "vertical"].forEach(
        function (mode) {
          var storedOffset = parsed.offsets[mode];

          if (!storedOffset) {
            return;
          }

          if (mode === "surface") {
            if (finiteNumber(storedOffset.x)) {
              state.offsets.surface.x = storedOffset.x;
            }

            if (finiteNumber(storedOffset.y)) {
              state.offsets.surface.y = storedOffset.y;
            }
          } else if (finiteNumber(storedOffset.angle)) {
            state.offsets[mode].angle = storedOffset.angle;
          }

          state.offsets[mode].active =
            storedOffset.active === true;
        }
      );
    } catch (error) {
      state.tolerance = 0.5;
      state.offsets = copyDefaultOffsets();
    }
  }

  function saveSettings() {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          tolerance: state.tolerance,
          offsets: state.offsets,
        })
      );
    } catch (error) {
      // La medición puede continuar sin almacenamiento local.
    }
  }

  function average(values) {
    if (!values.length) {
      return 0;
    }

    return (
      values.reduce(function (total, value) {
        return total + value;
      }, 0) / values.length
    );
  }

  function standardDeviation(values) {
    if (values.length < 2) {
      return Infinity;
    }

    var mean = average(values);

    var variance =
      values.reduce(function (total, value) {
        var difference = value - mean;

        return total + difference * difference;
      }, 0) / values.length;

    return Math.sqrt(variance);
  }

  function setMessage(message, type) {
    elements.message.textContent = message;

    elements.message.classList.remove(
      "level-message-success",
      "level-message-warning",
      "level-message-error"
    );

    if (type) {
      elements.message.classList.add(
        "level-message-" + type
      );
    }
  }

  function setStatus(statusName, message) {
    elements.card.dataset.state = statusName;
    elements.status.textContent = message;

    elements.dot.className = "dot level-sensor-dot";

    if (statusName === "level") {
      elements.dot.classList.add("level-dot-success");
    } else if (statusName === "near") {
      elements.dot.classList.add("level-dot-warning");
    } else if (
      statusName === "off" ||
      statusName === "waiting"
    ) {
      elements.dot.classList.add("level-dot-active");
    } else if (statusName === "error") {
      elements.dot.classList.add("level-dot-error");
    }
  }

  function getScreenAngle() {
    var angle = 0;

    if (
      window.screen &&
      window.screen.orientation &&
      finiteNumber(window.screen.orientation.angle)
    ) {
      angle = window.screen.orientation.angle;
    } else if (finiteNumber(window.orientation)) {
      angle = window.orientation;
    }

    return ((angle % 360) + 360) % 360;
  }

  function rotateFlatAngles(x, y) {
    var radians = (-getScreenAngle() * Math.PI) / 180;
    var cosine = Math.cos(radians);
    var sine = Math.sin(radians);

    return {
      x: x * cosine - y * sine,
      y: x * sine + y * cosine,
    };
  }

  function detectMode(gravity) {
    var magnitude = Math.hypot(
      gravity.x,
      gravity.y,
      gravity.z
    );

    if (!finiteNumber(magnitude) || magnitude < 1) {
      return null;
    }

    var x = Math.abs(gravity.x) / magnitude;
    var y = Math.abs(gravity.y) / magnitude;
    var z = Math.abs(gravity.z) / magnitude;

    /*
     * Z dominante: pantalla paralela a la superficie.
     */
    if (z >= 0.72) {
      return "surface";
    }

    /*
     * X dominante: teléfono apoyado sobre un borde largo.
     */
    if (
      x >= 0.62 &&
      x > y + 0.04 &&
      x > z + 0.04
    ) {
      return "horizontal";
    }

    /*
     * Y dominante: teléfono apoyado sobre un borde corto.
     */
    if (
      y >= 0.62 &&
      y > x + 0.04 &&
      y > z + 0.04
    ) {
      return "vertical";
    }

    return null;
  }

  function updateDetectedMode(candidate) {
    if (!candidate) {
      elements.mode.textContent = state.mode
        ? MODE_INFORMATION[state.mode].title
        : "Cambiando posición";

      return;
    }

    if (candidate === state.mode) {
      state.modeCandidate = null;
      state.modeCandidateCount = 0;
      return;
    }

    if (candidate !== state.modeCandidate) {
      state.modeCandidate = candidate;
      state.modeCandidateCount = 1;
      return;
    }

    state.modeCandidateCount += 1;

    if (
      state.modeCandidateCount >=
      MODE_CONFIRMATION_SAMPLES
    ) {
      changeMode(candidate);
    }
  }

  function changeMode(mode) {
    state.mode = mode;
    state.modeCandidate = null;
    state.modeCandidateCount = 0;

    state.raw = null;
    state.corrected = null;
    state.samples = [];

    state.stableLevelCounter = 0;
    state.vibrationSent = false;

    elements.visual.dataset.mode = mode;

    elements.mode.textContent =
      MODE_INFORMATION[mode].title;

    elements.modeDescription.textContent =
      MODE_INFORMATION[mode].description;

    elements.surfaceReadings.hidden =
      mode !== "surface";

    elements.edgeReading.hidden =
      mode === "surface";

    elements.angleLabel.textContent =
      MODE_INFORMATION[mode].angleLabel;

    elements.zero.disabled = !state.hasReading;

    updateCalibrationLabel();
    resetVisuals();

    setStatus("waiting", "Estabilizando");

    setMessage(
      "Posición detectada automáticamente. Mantén el teléfono quieto."
    );
  }

  function calculateRawReading(gravity) {
    if (!state.mode) {
      return null;
    }

    var magnitude = Math.hypot(
      gravity.x,
      gravity.y,
      gravity.z
    );

    if (!finiteNumber(magnitude) || magnitude < 1) {
      return null;
    }

    var physicalX = toDegrees(
      Math.asin(
        clamp(gravity.x / magnitude, -1, 1)
      )
    );

    var physicalY = toDegrees(
      Math.asin(
        clamp(gravity.y / magnitude, -1, 1)
      )
    );

    if (state.mode === "surface") {
      return {
        physicalX: physicalX,
        physicalY: physicalY,
      };
    }

    if (state.mode === "horizontal") {
      /*
       * Cuando X domina, el borde largo corresponde al eje Y.
       * El signo de X normaliza la lectura al cambiar de lado.
       */
      return {
        angle:
          physicalY *
          (gravity.x >= 0 ? 1 : -1),
      };
    }

    /*
     * Cuando Y domina, el eje largo está aproximadamente vertical.
     * La desviación lateral se obtiene mediante el eje X.
     */
    return {
      angle:
        physicalX *
        (gravity.y >= 0 ? 1 : -1),
    };
  }

  function applyOffset(raw) {
    var offset = state.offsets[state.mode];

    if (state.mode === "surface") {
      var physicalCorrected = {
        x: raw.physicalX - offset.x,
        y: raw.physicalY - offset.y,
      };

      return rotateFlatAngles(
        physicalCorrected.x,
        physicalCorrected.y
      );
    }

    return {
      angle: raw.angle - offset.angle,
    };
  }

  function addStabilitySample(corrected) {
    state.samples.push(corrected);

    if (state.samples.length > MAX_STABILITY_SAMPLES) {
      state.samples.shift();
    }
  }

  function getStability() {
    if (
      state.samples.length <
      MIN_STABILITY_SAMPLES
    ) {
      return Infinity;
    }

    var recent = state.samples.slice(
      -MIN_STABILITY_SAMPLES
    );

    if (state.mode === "surface") {
      var xDeviation = standardDeviation(
        recent.map(function (sample) {
          return sample.x;
        })
      );

      var yDeviation = standardDeviation(
        recent.map(function (sample) {
          return sample.y;
        })
      );

      return Math.max(xDeviation, yDeviation);
    }

    return standardDeviation(
      recent.map(function (sample) {
        return sample.angle;
      })
    );
  }

  function readingIsStable() {
    return getStability() <= STABILITY_LIMIT;
  }

  function updateStability() {
    if (
      state.samples.length <
      MIN_STABILITY_SAMPLES
    ) {
      elements.stability.textContent = "Estabilizando";
      elements.stability.dataset.stable = "false";
      return;
    }

    if (readingIsStable()) {
      elements.stability.textContent = "Lectura estable";
      elements.stability.dataset.stable = "true";
    } else {
      elements.stability.textContent = "En movimiento";
      elements.stability.dataset.stable = "false";
    }
  }

  function updateSurfaceBubble(reading) {
    var size = elements.surface.clientWidth;
    var bubbleSize = elements.bubble.offsetWidth;

    var travel = Math.max(
      0,
      (size - bubbleSize) / 2 - 18
    );

    var visualLimit = Math.max(
      4,
      state.tolerance * 7
    );

    var moveX =
      clamp(reading.x / visualLimit, -1, 1) *
      travel;

    /*
     * CSS crece hacia abajo, por lo que el eje vertical se invierte.
     */
    var moveY =
      clamp(-reading.y / visualLimit, -1, 1) *
      travel;

    elements.bubble.style.transform =
      "translate(calc(-50% + " +
      moveX.toFixed(1) +
      "px), calc(-50% + " +
      moveY.toFixed(1) +
      "px))";
  }

  function updateTubeBubble(reading) {
    var width = elements.tube.clientWidth;
    var bubbleWidth = elements.tubeBubble.offsetWidth;

    var travel = Math.max(
      0,
      (width - bubbleWidth) / 2 - 20
    );

    var visualLimit = Math.max(
      4,
      state.tolerance * 8
    );

    var move =
      clamp(reading.angle / visualLimit, -1, 1) *
      travel;

    elements.tubeBubble.style.transform =
      "translate(calc(-50% + " +
      move.toFixed(1) +
      "px), -50%)";
  }

  function updateDirection(angle) {
    if (Math.abs(angle) <= state.tolerance) {
      elements.direction.textContent = "Centrado";
      return;
    }

    if (state.mode === "vertical") {
      elements.direction.textContent =
        angle > 0
          ? "Inclinado hacia la derecha"
          : "Inclinado hacia la izquierda";

      return;
    }

    elements.direction.textContent =
      angle > 0
        ? "Un extremo está más alto"
        : "El extremo opuesto está más alto";
  }

  function updateLevelState(metric) {
    var stable = readingIsStable();

    if (metric <= state.tolerance && stable) {
      setStatus("level", "Nivelado");
      state.stableLevelCounter += 1;

      if (
        state.stableLevelCounter >= 10 &&
        !state.vibrationSent
      ) {
        if (navigator.vibrate) {
          navigator.vibrate(80);
        }

        state.vibrationSent = true;
      }

      return;
    }

    state.stableLevelCounter = 0;
    state.vibrationSent = false;

    if (metric <= state.tolerance) {
      setStatus("near", "Dentro de tolerancia");
    } else if (metric <= state.tolerance * 2) {
      setStatus("near", "Casi nivelado");
    } else {
      setStatus("off", "Fuera de nivel");
    }
  }

  function renderReading(reading) {
    updateStability();

    if (state.mode === "surface") {
      var total = Math.hypot(
        reading.x,
        reading.y
      );

      elements.x.textContent =
        reading.x.toFixed(1) + "°";

      elements.y.textContent =
        reading.y.toFixed(1) + "°";

      elements.total.textContent =
        total.toFixed(1) + "°";

      updateSurfaceBubble(reading);
      updateLevelState(total);
      return;
    }

    elements.angle.textContent =
      reading.angle.toFixed(1) + "°";

    updateDirection(reading.angle);
    updateTubeBubble(reading);
    updateLevelState(Math.abs(reading.angle));
  }

  function handleMotion(event) {
    if (!state.running) {
      return;
    }

    var acceleration =
      event.accelerationIncludingGravity;

    if (
      !acceleration ||
      !finiteNumber(acceleration.x) ||
      !finiteNumber(acceleration.y) ||
      !finiteNumber(acceleration.z)
    ) {
      return;
    }

    if (!state.gravity) {
      state.gravity = {
        x: acceleration.x,
        y: acceleration.y,
        z: acceleration.z,
      };
    } else {
      state.gravity.x +=
        FILTER_ALPHA *
        (acceleration.x - state.gravity.x);

      state.gravity.y +=
        FILTER_ALPHA *
        (acceleration.y - state.gravity.y);

      state.gravity.z +=
        FILTER_ALPHA *
        (acceleration.z - state.gravity.z);
    }

    var candidate = detectMode(state.gravity);

    updateDetectedMode(candidate);

    if (!state.mode) {
      setStatus("waiting", "Detectando posición");
      return;
    }

    var raw = calculateRawReading(state.gravity);

    if (!raw) {
      return;
    }

    state.hasReading = true;
    state.raw = raw;
    state.corrected = applyOffset(raw);

    addStabilitySample(state.corrected);
    renderReading(state.corrected);

    elements.zero.disabled = false;

    if (state.sensorTimeout) {
      window.clearTimeout(state.sensorTimeout);
      state.sensorTimeout = null;
    }
  }

  async function requestMotionPermission() {
    if (!("DeviceMotionEvent" in window)) {
      throw new Error(
        "Este navegador no proporciona acceso al acelerómetro."
      );
    }

    if (
      typeof window.DeviceMotionEvent.requestPermission ===
      "function"
    ) {
      var permission =
        await window.DeviceMotionEvent.requestPermission();

      if (permission !== "granted") {
        throw new Error(
          "El permiso de movimiento fue rechazado."
        );
      }
    }
  }

  async function startSensor() {
    if (state.running) {
      return;
    }

    if (!window.isSecureContext) {
      setStatus("error", "Se requiere HTTPS");

      setMessage(
        "El navegador requiere una conexión HTTPS para acceder al sensor.",
        "error"
      );

      return;
    }

    try {
      setStatus("waiting", "Solicitando permiso");

      setMessage(
        "Acepta el permiso de movimiento cuando aparezca.",
        "warning"
      );

      await requestMotionPermission();

      state.running = true;
      state.hasReading = false;
      state.gravity = null;

      state.mode = null;
      state.modeCandidate = null;
      state.modeCandidateCount = 0;

      state.raw = null;
      state.corrected = null;
      state.samples = [];

      state.stableLevelCounter = 0;
      state.vibrationSent = false;

      elements.visual.dataset.mode = "detecting";

      elements.mode.textContent = "Detectando posición";
      elements.modeDescription.textContent =
        "Coloca el teléfono en la posición que deseas medir.";

      elements.start.disabled = true;
      elements.stop.disabled = false;
      elements.zero.disabled = true;

      window.addEventListener(
        "devicemotion",
        handleMotion,
        true
      );

      setStatus("waiting", "Esperando sensor");

      state.sensorTimeout = window.setTimeout(
        function () {
          if (!state.hasReading) {
            setStatus("error", "Sin datos del sensor");

            setMessage(
              "No se recibieron datos. Abre la aplicación directamente en Safari o Chrome y revisa los permisos.",
              "error"
            );
          }
        },
        4000
      );
    } catch (error) {
      state.running = false;

      setStatus("error", "Sensor no disponible");
      setMessage(error.message, "error");

      elements.start.disabled = false;
      elements.stop.disabled = true;
      elements.zero.disabled = true;
    }
  }

  function stopSensor() {
    window.removeEventListener(
      "devicemotion",
      handleMotion,
      true
    );

    if (state.sensorTimeout) {
      window.clearTimeout(state.sensorTimeout);
      state.sensorTimeout = null;
    }

    state.running = false;
    state.hasReading = false;
    state.gravity = null;

    state.mode = null;
    state.modeCandidate = null;
    state.modeCandidateCount = 0;

    state.raw = null;
    state.corrected = null;
    state.samples = [];

    elements.start.disabled = false;
    elements.stop.disabled = true;
    elements.zero.disabled = true;

    elements.mode.textContent = "Esperando sensor";
    elements.modeDescription.textContent =
      "Activa el sensor para comenzar.";

    elements.stability.textContent = "Sin lectura";
    elements.stability.dataset.stable = "false";

    elements.visual.dataset.mode = "detecting";

    setStatus("stopped", "Sensor detenido");

    setMessage(
      "Pulsa “Activar nivelador” para comenzar una nueva medición."
    );

    resetVisuals();
  }

  function setRelativeZero() {
    if (
      !state.running ||
      !state.hasReading ||
      !state.mode ||
      !state.raw
    ) {
      setMessage(
        "Espera una lectura válida antes de establecer el cero.",
        "warning"
      );

      return;
    }

    if (!readingIsStable()) {
      setMessage(
        "Mantén el teléfono quieto hasta que aparezca “Lectura estable”.",
        "warning"
      );

      return;
    }

    if (state.mode === "surface") {
      state.offsets.surface.x =
        state.raw.physicalX;

      state.offsets.surface.y =
        state.raw.physicalY;

      state.offsets.surface.active = true;
    } else {
      state.offsets[state.mode].angle =
        state.raw.angle;

      state.offsets[state.mode].active = true;
    }

    saveSettings();

    state.samples = [];
    state.corrected = applyOffset(state.raw);

    updateCalibrationLabel();
    renderReading(state.corrected);

    setMessage(
      "La posición actual fue establecida como cero relativo para este modo.",
      "success"
    );

    if (navigator.vibrate) {
      navigator.vibrate(50);
    }
  }

  function resetRelativeZero() {
    if (!state.mode) {
      setMessage(
        "Activa el sensor para detectar primero una posición.",
        "warning"
      );

      return;
    }

    if (state.mode === "surface") {
      state.offsets.surface = {
        x: 0,
        y: 0,
        active: false,
      };
    } else {
      state.offsets[state.mode] = {
        angle: 0,
        active: false,
      };
    }

    saveSettings();

    state.samples = [];

    if (state.raw) {
      state.corrected = applyOffset(state.raw);
      renderReading(state.corrected);
    }

    updateCalibrationLabel();

    setMessage(
      "Se restableció la medición absoluta para el modo actual.",
      "success"
    );
  }

  function updateCalibrationLabel() {
    if (!state.mode) {
      elements.calibrationState.textContent =
        "Gravedad absoluta";

      return;
    }

    elements.calibrationState.textContent =
      state.offsets[state.mode].active
        ? "Cero relativo activo"
        : "Gravedad absoluta";
  }

  function updateTolerance() {
    var tolerance = Number(elements.tolerance.value);

    if (!finiteNumber(tolerance)) {
      tolerance = 0.5;
    }

    state.tolerance = clamp(tolerance, 0.2, 2);

    elements.toleranceValue.textContent =
      "±" + state.tolerance.toFixed(1) + "°";

    saveSettings();

    if (state.corrected) {
      renderReading(state.corrected);
    }
  }

  function resetVisuals() {
    elements.bubble.style.transform =
      "translate(-50%, -50%)";

    elements.tubeBubble.style.transform =
      "translate(-50%, -50%)";

    elements.x.textContent = "0.0°";
    elements.y.textContent = "0.0°";
    elements.total.textContent = "0.0°";

    elements.angle.textContent = "0.0°";
    elements.direction.textContent = "Centrado";
  }

  function initialize() {
    loadSettings();

    elements.tolerance.value =
      state.tolerance.toFixed(1);

    elements.toleranceValue.textContent =
      "±" + state.tolerance.toFixed(1) + "°";

    elements.start.addEventListener(
      "click",
      startSensor
    );

    elements.stop.addEventListener(
      "click",
      stopSensor
    );

    elements.zero.addEventListener(
      "click",
      setRelativeZero
    );

    elements.reset.addEventListener(
      "click",
      resetRelativeZero
    );

    elements.tolerance.addEventListener(
      "input",
      updateTolerance
    );

    window.addEventListener(
      "orientationchange",
      function () {
        if (
          state.mode === "surface" &&
          state.raw
        ) {
          state.corrected = applyOffset(state.raw);
          renderReading(state.corrected);
        }
      }
    );

    window.addEventListener(
      "resize",
      function () {
        if (state.corrected) {
          renderReading(state.corrected);
        }
      }
    );

    window.addEventListener(
      "beforeunload",
      function () {
        window.removeEventListener(
          "devicemotion",
          handleMotion,
          true
        );
      }
    );
  }

  initialize();
})();