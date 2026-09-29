(function () {
  "use strict";

  var viewer =
    document.getElementById(
      "product-model-viewer"
    );

  var rotateButton =
    document.querySelector(
      "[data-simple-rotate]"
    );

  var zoomButton =
    document.querySelector(
      "[data-simple-zoom]"
    );

  var resetButton =
    document.querySelector(
      "[data-simple-reset]"
    );

  if (
    !viewer
    || !rotateButton
    || !zoomButton
    || !resetButton
  ) {
    return;
  }


  function jumpCamera() {

    if (
      typeof viewer.jumpCameraToGoal
      === "function"
    ) {
      viewer.jumpCameraToGoal();
    }

  }


  function enableButtons() {

    rotateButton.disabled = false;
    zoomButton.disabled = false;
    resetButton.disabled = false;

  }


  customElements
    .whenDefined("model-viewer")
    .then(function () {

      if (viewer.loaded) {

        enableButtons();

      } else {

        viewer.addEventListener(
          "load",
          enableButtons,
          {
            once: true,
          }
        );

      }

    });


  /*
   * GIRAR
   * Gira 15 grados a la derecha
   * conservando la distancia actual.
   */
  rotateButton.addEventListener(
    "click",
    function () {

      var orbit =
        viewer.getCameraOrbit();

      var fifteenDegrees =
        Math.PI / 12;

      viewer.cameraOrbit =
        (
          (orbit.theta + fifteenDegrees)
          + "rad "
          + orbit.phi
          + "rad "
          + orbit.radius
          + "m"
        );

      jumpCamera();

    }
  );


  /*
   * ACERCAR
   * Reduce la distancia de la cámara
   * un 15% en cada pulsación.
   */
  zoomButton.addEventListener(
    "click",
    function () {

      var orbit =
        viewer.getCameraOrbit();

      var newRadius =
        orbit.radius * 0.85;

      viewer.cameraOrbit =
        (
          orbit.theta
          + "rad "
          + orbit.phi
          + "rad "
          + newRadius
          + "m"
        );

      jumpCamera();

    }
  );


  /*
   * CENTRAR
   * Regresa a la vista inicial.
   */
  resetButton.addEventListener(
    "click",
    function () {

      viewer.cameraTarget =
        "auto auto auto";

      viewer.cameraOrbit =
        "0deg 75deg 105%";

      jumpCamera();

    }
  );

})();
