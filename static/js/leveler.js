(function () {
  "use strict";

  var elements = {
    card: document.getElementById("leveler-card"),
    stage: document.getElementById("level-stage"),
    bubble: document.getElementById("level-bubble"),
    dot: document.getElementById("level-dot"),
    status: document.getElementById("level-status"),
    x: document.getElementById("level-x"),
    y: document.getElementById("level-y"),
    total: document.getElementById("level-total"),
    tolerance: document.getElementById("level-tolerance"),
    toleranceValue: document.getElementById("level-tolerance-value"),
    start: document.getElementById("btn-level-start"),
    stop: document.getElementById("btn-level-stop"),
    calibrate: document.getElementById("btn-level-calibrate"),
    reset: document.getElementById("btn-level-reset"),
    message: document.getElementById("level-message"),
    calibrationState: document.getElementById("level-calibration-state"),
  };

  var STORAGE = {
    offsetX: "smav_leveler_offset_x",
    offsetY: "smav_leveler_offset_y",
    tolerance: "smav_leveler_tolerance",
  };

  var state = {
    running: false,
    hasReading: false,
    initialized: false,
    rawX: 0,
    rawY: 0,
    offsetX: loadNumber(STORAGE.offsetX, 0),
    offsetY: loadNumber(STORAGE.offsetY, 0),
    tolerance: loadNumber(STORAGE.tolerance, 0.5),
    stableSamples: 0,
    vibrationSent: false,
    watchdog: null,
  };

  var SMOOTHING = 0.16;
  var REQUIRED_STABLE_SAMPLES = 12;

  function loadNumber(key, fallback) {
    try {
      var value = Number(window.localStorage.getItem(key));
      return Number.isFinite(value) ? value : fallback;
    } catch (error) {
      return fallback;
    }
  }

  function saveNumber(key, value) {
    try {
      window.localStorage.setItem(key, String(value));
    } catch (error) {
      // La aplicación puede seguir funcionando sin almacenamiento local.
    }
  }

  function removeStoredValue(key) {
    try {
      window.localStorage.removeItem(key);
    } catch (error) {
      // No se requiere acción adicional.
    }
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function getScreenAngle() {
    var angle = 0;

    if (
      window.screen &&
      window.screen.orientation &&
      Number.isFinite(window.screen.orientation.angle)
    ) {
      angle = window.screen.orientation.angle;
    } else if (Number.isFinite(window.orientation)) {
      angle = window.orientation;
    }

    angle = ((angle % 360) + 360) % 360;

    return Math.round(angle / 90) * 90;
  }

  function convertToScreenAxes(beta, gamma) {
    var angle = (getScreenAngle() * Math.PI) / 180;
    var cos = Math.cos(angle);
    var sin = Math.sin(angle);

    /*
     * En vertical:
     * gamma representa izquierda/derecha.
     * beta representa frente/atrás.
     *
     * Se rotan los ejes para conservar el comportamiento cuando la pantalla
     * cambia entre orientación vertical y horizontal.
     */
    return {
      x: gamma * cos + beta * sin,
      y: beta * cos - gamma * sin,
    };
  }

  function setMessage(message, type) {
    elements.message.textContent = message;
    elements.message.classList.remove(
      "level-message-success",
      "level-message-warning",
      "level-message-error"
    );

    if (type) {
      elements.message.classList.add("level-message-" + type);
    }
  }

  function setStatus(stateName, message) {
    elements.card.dataset.state = stateName;
    elements.status.textContent = message;

    elements.dot.className = "dot level-sensor-dot";

    if (stateName === "level") {
      elements.dot.classList.add("level-dot-success");
    } else if (stateName === "near") {
      elements.dot.classList.add("level-dot-warning");
    } else if (stateName === "off") {
      elements.dot.classList.add("level-dot-active");
    } else if (stateName === "error") {
      elements.dot.classList.add("level-dot-error");
    }
  }

  function updateBubble(x, y) {
    var stageWidth = elements.stage.clientWidth;
    var bubbleWidth = elements.bubble.offsetWidth;

    var travel = Math.max(0, (stageWidth - bubbleWidth) / 2 - 16);
    var visualLimit = Math.max(4, state.tolerance * 5);

    var translateX =
      clamp(x / visualLimit, -1, 1) * travel;

    var translateY =
      clamp(y / visualLimit, -1, 1) * travel;

    elements.bubble.style.transform =
      "translate(calc(-50% + " +
      translateX.toFixed(1) +
      "px), calc(-50% + " +
      translateY.toFixed(1) +
      "px))";
  }

  function updateLevelState(x, y) {
    var magnitude = Math.hypot(x, y);

    elements.x.textContent = x.toFixed(2) + "°";
    elements.y.textContent = y.toFixed(2) + "°";
    elements.total.textContent = magnitude.toFixed(2) + "°";

    updateBubble(x, y);

    if (magnitude <= state.tolerance) {
      setStatus("level", "Nivelado");
      state.stableSamples += 1;

      if (
        state.stableSamples >= REQUIRED_STABLE_SAMPLES &&
        !state.vibrationSent
      ) {
        if (navigator.vibrate) {
          navigator.vibrate(80);
        }

        state.vibrationSent = true;
      }
    } else if (magnitude <= state.tolerance * 2) {
      setStatus("near", "Casi nivelado");
      state.stableSamples = 0;
      state.vibrationSent = false;
    } else {
      setStatus("off", "Fuera de nivel");
      state.stableSamples = 0;
      state.vibrationSent = false;
    }
  }

  function handleOrientation(event) {
    if (
      !Number.isFinite(event.beta) ||
      !Number.isFinite(event.gamma)
    ) {
      return;
    }

    /*
     * Un beta cercano a ±180 suele indicar que el teléfono está boca abajo.
     * El nivelador está diseñado para trabajar con la pantalla hacia arriba.
     */
    if (Math.abs(event.beta) > 90) {
      setStatus("near", "Coloca la pantalla hacia arriba");
      setMessage(
        "Gira el teléfono y colócalo con la pantalla orientada hacia arriba.",
        "warning"
      );
      return;
    }

    var axes = convertToScreenAxes(event.beta, event.gamma);

    if (!state.initialized) {
      state.rawX = axes.x;
      state.rawY = axes.y;
      state.initialized = true;
    } else {
      state.rawX += SMOOTHING * (axes.x - state.rawX);
      state.rawY += SMOOTHING * (axes.y - state.rawY);
    }

    state.hasReading = true;

    if (state.watchdog) {
      window.clearTimeout(state.watchdog);
      state.watchdog = null;
    }

    elements.calibrate.disabled = false;

    var correctedX = state.rawX - state.offsetX;
    var correctedY = state.rawY - state.offsetY;

    updateLevelState(correctedX, correctedY);
  }

  async function requestSensorPermission() {
    if (!("DeviceOrientationEvent" in window)) {
      throw new Error(
        "Este navegador no proporciona acceso al sensor de orientación."
      );
    }

    if (
      typeof window.DeviceOrientationEvent.requestPermission === "function"
    ) {
      var permission =
        await window.DeviceOrientationEvent.requestPermission();

      if (permission !== "granted") {
        throw new Error(
          "El permiso del sensor fue rechazado. Actívalo desde la configuración del navegador."
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
        "Los sensores del teléfono requieren una conexión segura HTTPS.",
        "error"
      );
      return;
    }

    try {
      setStatus("waiting", "Solicitando permiso");
      setMessage(
        "Acepta el permiso de movimiento y orientación cuando aparezca.",
        "warning"
      );

      await requestSensorPermission();

      state.running = true;
      state.hasReading = false;
      state.initialized = false;
      state.stableSamples = 0;
      state.vibrationSent = false;

      window.addEventListener(
        "deviceorientation",
        handleOrientation,
        true
      );

      elements.start.disabled = true;
      elements.stop.disabled = false;
      elements.calibrate.disabled = true;

      setStatus("waiting", "Esperando sensor");
      setMessage(
        "Mantén el teléfono quieto durante unos segundos para estabilizar la lectura."
      );

      state.watchdog = window.setTimeout(function () {
        if (!state.hasReading) {
          setStatus("error", "Sin datos del sensor");
          setMessage(
            "No se recibieron datos. Abre la aplicación directamente en el navegador del teléfono y revisa los permisos.",
            "error"
          );
        }
      }, 3000);
    } catch (error) {
      state.running = false;
      setStatus("error", "Sensor no disponible");
      setMessage(error.message, "error");

      elements.start.disabled = false;
      elements.stop.disabled = true;
      elements.calibrate.disabled = true;
    }
  }

  function stopSensor() {
    window.removeEventListener(
      "deviceorientation",
      handleOrientation,
      true
    );

    if (state.watchdog) {
      window.clearTimeout(state.watchdog);
      state.watchdog = null;
    }

    state.running = false;
    state.hasReading = false;
    state.initialized = false;
    state.stableSamples = 0;
    state.vibrationSent = false;

    elements.start.disabled = false;
    elements.stop.disabled = true;
    elements.calibrate.disabled = true;

    setStatus("stopped", "Sensor detenido");
    setMessage(
      "Pulsa “Activar sensor” para comenzar una nueva medición."
    );
  }

  function calibrateSensor() {
    if (!state.running || !state.hasReading) {
      setMessage(
        "Activa el sensor y espera una lectura antes de calibrar.",
        "warning"
      );
      return;
    }

    state.offsetX = state.rawX;
    state.offsetY = state.rawY;

    saveNumber(STORAGE.offsetX, state.offsetX);
    saveNumber(STORAGE.offsetY, state.offsetY);

    elements.calibrationState.textContent =
      "Calibración personalizada activa";

    updateLevelState(0, 0);

    setMessage(
      "Calibración guardada. Esta posición se utilizará como referencia de 0°.",
      "success"
    );

    if (navigator.vibrate) {
      navigator.vibrate(50);
    }
  }

  function resetCalibration() {
    state.offsetX = 0;
    state.offsetY = 0;

    removeStoredValue(STORAGE.offsetX);
    removeStoredValue(STORAGE.offsetY);

    elements.calibrationState.textContent =
      "Sin ajuste personalizado";

    if (state.running && state.hasReading) {
      updateLevelState(state.rawX, state.rawY);
    }

    setMessage(
      "La calibración personalizada fue eliminada.",
      "success"
    );
  }

  function updateTolerance() {
    var tolerance = Number(elements.tolerance.value);

    if (!Number.isFinite(tolerance)) {
      tolerance = 0.5;
    }

    state.tolerance = tolerance;
    elements.toleranceValue.textContent =
      "±" + tolerance.toFixed(1) + "°";

    saveNumber(STORAGE.tolerance, tolerance);

    if (state.running && state.hasReading) {
      updateLevelState(
        state.rawX - state.offsetX,
        state.rawY - state.offsetY
      );
    }
  }

  function initialize() {
    state.tolerance = clamp(state.tolerance, 0.2, 2);

    elements.tolerance.value = state.tolerance.toFixed(1);
    elements.toleranceValue.textContent =
      "±" + state.tolerance.toFixed(1) + "°";

    var hasCalibration =
      Math.abs(state.offsetX) > 0.0001 ||
      Math.abs(state.offsetY) > 0.0001;

    elements.calibrationState.textContent = hasCalibration
      ? "Calibración personalizada activa"
      : "Sin ajuste personalizado";

    elements.start.addEventListener("click", startSensor);
    elements.stop.addEventListener("click", stopSensor);
    elements.calibrate.addEventListener("click", calibrateSensor);
    elements.reset.addEventListener("click", resetCalibration);
    elements.tolerance.addEventListener("input", updateTolerance);

    window.addEventListener("resize", function () {
      if (state.running && state.hasReading) {
        updateBubble(
          state.rawX - state.offsetX,
          state.rawY - state.offsetY
        );
      }
    });

    window.addEventListener("beforeunload", function () {
      window.removeEventListener(
        "deviceorientation",
        handleOrientation,
        true
      );
    });
  }

  initialize();
})();