const viewer = document.getElementById(
        "product-model-viewer"
    );

    const panel = document.getElementById(
        "experience-panel"
    );

    const controls3D = document.getElementById(
        "controls-3d"
    );

    const controlsAR = document.getElementById(
        "controls-ar"
    );

    const instructions = document.getElementById(
        "mode-instructions"
    );

    const viewerFeedback = document.getElementById(
        "viewer-feedback"
    );

    const deviceARHelp = document.getElementById(
        "device-ar-help"
    );

    const arMessage = document.getElementById(
        "ar-message"
    );

    const launchARButton = document.getElementById(
        "launch-ar"
    );

    const open3DButton = document.getElementById(
        "open-3d"
    );

    const openARButton = document.getElementById(
        "open-ar"
    );

    const viewButtons = document.querySelectorAll(
        "[data-view-rotate], [data-view-reset]"
    );


    const userAgent =
        navigator.userAgent || "";

    const isIOS =
        /iPad|iPhone|iPod/.test(userAgent)
        || (
            navigator.platform === "MacIntel"
            && navigator.maxTouchPoints > 1
        );

    const isAndroid =
        /Android/i.test(userAgent);

    const isMobile =
        isIOS
        || isAndroid
        || /Mobile/i.test(userAgent);


    let modelReady = false;

    /*
     * Ángulo horizontal utilizado por los
     * botones del visor normal.
     */
    let cameraTheta = 0;


    /*
     * Vista inicial del Modelo 3D.
     *
     * Se utiliza como punto de referencia para calcular
     * cuánto giró o acercó el usuario el producto.
     */
    let referenceOrbit = null;


    /*
     * Vista copiada desde el Modelo 3D para RA.
     */
    const copiedARView = {
        pitch: 0,
        yaw: 0,
        scale: 1,
    };


    /*
     * Transformaciones actuales durante WebXR.
     */
    let arPitch = 0;
    let arRotationY = 0;
    let arScale = 1;


    /*
     * Sirve para restaurar el visor cuando el usuario
     * vuelve desde Quick Look en iPhone.
     */
    let arLaunchInProgress = false;
    let pageWasHiddenForAR = false;


    function clamp(
        value,
        minimum,
        maximum
    ) {
        return Math.min(
            maximum,
            Math.max(minimum, value)
        );
    }


    function radiansToDegrees(radians) {
        return radians * 180 / Math.PI;
    }


    function normalizeDegrees(value) {
        let result = value % 360;

        if (result > 180) {
            result -= 360;
        }

        if (result < -180) {
            result += 360;
        }

        return Math.round(result * 10) / 10;
    }


    function setViewerFeedback(message) {
        if (viewerFeedback) {
            viewerFeedback.textContent = message;
        }
    }


    function setARMessage(
        message,
        messageType = "error"
    ) {
        arMessage.textContent = message;

        arMessage.classList.remove(
            "is-information",
            "is-success"
        );

        if (messageType === "information") {
            arMessage.classList.add(
                "is-information"
            );
        }

        if (messageType === "success") {
            arMessage.classList.add(
                "is-success"
            );
        }
    }


    function setViewButtonsEnabled(enabled) {
        viewButtons.forEach((button) => {
            button.disabled = !enabled;
        });
    }


    /*
     * Guarda la cámara inicial del Modelo 3D.
     *
     * Esa cámara corresponde a:
     * 0 grados horizontal,
     * 75 grados vertical,
     * 105% de distancia.
     */
    function saveReferenceOrbit() {
        if (
            typeof viewer.getCameraOrbit
            !== "function"
        ) {
            return;
        }

        const orbit =
            viewer.getCameraOrbit();

        if (
            !orbit
            || !Number.isFinite(orbit.radius)
            || orbit.radius <= 0
        ) {
            return;
        }

        referenceOrbit = {
            theta: orbit.theta,
            phi: orbit.phi,
            radius: orbit.radius,
        };

        cameraTheta =
            radiansToDegrees(orbit.theta);
    }


    /*
     * Obtiene el ángulo actual de la cámara después
     * de que el usuario arrastró el modelo.
     */
    function synchronizeCameraTheta() {
        if (
            typeof viewer.getCameraOrbit
            !== "function"
        ) {
            return;
        }

        const currentOrbit =
            viewer.getCameraOrbit();

        if (
            currentOrbit
            && Number.isFinite(currentOrbit.theta)
        ) {
            cameraTheta =
                radiansToDegrees(
                    currentOrbit.theta
                );
        }
    }


    /*
     * Gira la cámara alrededor del producto.
     */
    function rotateCamera(degrees) {
        if (!modelReady) {
            setViewerFeedback(
                "Espera a que termine de cargar el modelo."
            );

            return;
        }

        synchronizeCameraTheta();

        cameraTheta += degrees;

        viewer.setAttribute(
            "camera-orbit",
            `${cameraTheta}deg 75deg 105%`
        );

        if (
            typeof viewer.jumpCameraToGoal
            === "function"
        ) {
            viewer.jumpCameraToGoal();
        }

        if (degrees < 0) {
            setViewerFeedback(
                "Vista girada hacia la izquierda."
            );
        } else {
            setViewerFeedback(
                "Vista girada hacia la derecha."
            );
        }
    }


    async function resetCamera() {

        if (!modelReady) {
            setViewerFeedback(
                "Espera a que termine de cargar el modelo."
            );
            return;
        }

        cameraTheta = 0;

        viewer.orientation =
            "0deg 0deg 0deg";

        viewer.scale =
            "1 1 1";

        if (
            typeof viewer.updateFraming
            === "function"
        ) {
            await viewer.updateFraming();
        }

        viewer.cameraTarget =
            "auto auto auto";

        viewer.fieldOfView =
            "auto";

        viewer.cameraOrbit =
            "0deg 75deg 105%";

        if (viewer.updateComplete) {
            await viewer.updateComplete;
        }

        if (
            typeof viewer.jumpCameraToGoal
            === "function"
        ) {
            viewer.jumpCameraToGoal();
        }

        requestAnimationFrame(
            function () {
                saveReferenceOrbit();
            }
        );

        setViewerFeedback(
            "Vista centrada al frente."
        );
    }


    /*
     * Convierte la cámara actual del Modelo 3D en una
     * rotación y escala reales del objeto.
     *
     * La cámara gira alrededor del producto en 3D.
     * En RA necesitamos hacer lo contrario:
     * girar el producto frente a la cámara.
     */
    function copyCurrent3DViewToAR() {
        if (
            typeof viewer.getCameraOrbit
            !== "function"
        ) {
            return false;
        }

        const currentOrbit =
            viewer.getCameraOrbit();

        if (
            !currentOrbit
            || !Number.isFinite(currentOrbit.radius)
            || currentOrbit.radius <= 0
        ) {
            return false;
        }

        if (!referenceOrbit) {
            referenceOrbit = {
                theta: 0,
                phi: 75 * Math.PI / 180,
                radius: currentOrbit.radius,
            };
        }


        /*
         * Horizontal:
         * mover la cámara hacia un lado equivale a girar
         * el producto en sentido contrario.
         */
        copiedARView.yaw =
            normalizeDegrees(
                radiansToDegrees(
                    referenceOrbit.theta
                    - currentOrbit.theta
                )
            );


        /*
         * Vertical:
         * si la cámara observa el objeto desde arriba,
         * inclinamos el producto para reproducir esa vista.
         */
        copiedARView.pitch =
            normalizeDegrees(
                radiansToDegrees(
                    referenceOrbit.phi
                    - currentOrbit.phi
                )
            );


        /*
         * Zoom:
         * cámara más cerca = modelo inicialmente más grande.
         * Se limita para evitar tamaños extremos en RA.
         */
        copiedARView.scale =
            clamp(
                referenceOrbit.radius
                / currentOrbit.radius,
                0.4,
                2.5
            );


        arPitch =
            copiedARView.pitch;

        arRotationY =
            copiedARView.yaw;

        arScale =
            copiedARView.scale;


        applyARTransformations();

        return true;
    }


    /*
     * Aplica la vista copiada al modelo real.
     *
     * orientation usa:
     * roll, pitch y yaw.
     */
    function applyARTransformations() {
        viewer.setAttribute(
            "orientation",
            `0deg ${arPitch}deg ${arRotationY}deg`
        );

        arScale =
            clamp(arScale, 0.4, 2.5);

        viewer.setAttribute(
            "scale",
            `${arScale} ${arScale} ${arScale}`
        );
    }


    /*
     * El botón central de WebXR regresa al ángulo
     * copiado desde el Modelo 3D, no al frente absoluto.
     */
    function resetARTransformations() {
        arPitch =
            copiedARView.pitch;

        arRotationY =
            copiedARView.yaw;

        arScale =
            copiedARView.scale;

        applyARTransformations();
    }


    /*
     * Al regresar de RA, dejamos el Modelo 3D como estaba:
     * sin rotación física y con su cámara conservada.
     */
    function restoreNormal3DViewer() {
        viewer.setAttribute(
            "orientation",
            "0deg 0deg 0deg"
        );

        viewer.setAttribute(
            "scale",
            "1 1 1"
        );

        arLaunchInProgress = false;
        pageWasHiddenForAR = false;
    }


    function renderDeviceInstructions() {
        if (isIOS) {
            deviceARHelp.innerHTML = `
                <div class="device-help-heading">
                    <span
                        class="device-help-icon"
                        aria-hidden="true"
                    >
                        🍎
                    </span>

                    <div>
                        <strong>
                            Instrucciones para iPhone
                        </strong>

                        <span>
                            Se abrirá Quick Look de Apple
                        </span>
                    </div>
                </div>

                <ol class="device-help-steps">
                    <li>
                        Primero acomoda el Modelo 3D con el
                        ángulo y acercamiento que prefieras.
                    </li>

                    <li>
                        Presiona
                        <strong>
                            Abrir cámara con esta vista
                        </strong>.
                    </li>

                    <li>
                        En Quick Look selecciona
                        <strong>AR</strong>, cuando aparezca
                        la opción.
                    </li>

                    <li>
                        Apunta lentamente hacia el piso o una
                        mesa con buena iluminación.
                    </li>

                    <li>
                        El producto aparecerá con la vista
                        preparada en el Modelo 3D.
                    </li>
                </ol>

                <p class="device-help-note">
                    Quick Look usa los controles propios del
                    iPhone. Dentro de esa pantalla podrás mover
                    el producto y ajustar su tamaño con dos dedos.
                </p>
            `;

            return;
        }


        if (isAndroid) {
            deviceARHelp.innerHTML = `
                <div class="device-help-heading">
                    <span
                        class="device-help-icon"
                        aria-hidden="true"
                    >
                        📱
                    </span>

                    <div>
                        <strong>
                            Instrucciones para Android
                        </strong>

                        <span>
                            Usa Chrome y permite la cámara
                        </span>
                    </div>
                </div>

                <ol class="device-help-steps">
                    <li>
                        Acomoda primero el Modelo 3D con el
                        ángulo y acercamiento que prefieras.
                    </li>

                    <li>
                        Presiona
                        <strong>
                            Abrir cámara con esta vista
                        </strong>.
                    </li>

                    <li>
                        Acepta el permiso para utilizar
                        la cámara.
                    </li>

                    <li>
                        Mueve lentamente el teléfono apuntando
                        hacia una superficie plana.
                    </li>

                    <li>
                        El producto conservará la vista que
                        preparaste en el Modelo 3D.
                    </li>
                </ol>

                <p class="device-help-note">
                    En WebXR aparecerán botones para girar,
                    cambiar el tamaño y regresar a la vista
                    copiada del Modelo 3D.
                </p>
            `;

            return;
        }


        deviceARHelp.innerHTML = `
            <div class="device-help-heading">
                <span
                    class="device-help-icon"
                    aria-hidden="true"
                >
                    💻
                </span>

                <div>
                    <strong>
                        Abre esta página en un teléfono
                    </strong>

                    <span>
                        La computadora permite preparar la vista 3D
                    </span>
                </div>
            </div>

            <p class="
                device-help-note
                device-help-warning
            ">
                La realidad aumentada necesita la cámara y
                los sensores de un teléfono compatible.
                Acomoda aquí el Modelo 3D y abre esta página
                desde el teléfono para utilizar RA.
            </p>
        `;
    }


    function showMode(mode) {
        panel.hidden = false;

        const is3DMode =
            mode === "3d";

        controls3D.hidden =
            !is3DMode;

        controlsAR.hidden =
            is3DMode;

        document
            .querySelectorAll("[data-mode]")
            .forEach((button) => {
                const active =
                    button.dataset.mode === mode;

                button.classList.toggle(
                    "is-active",
                    active
                );

                button.setAttribute(
                    "aria-selected",
                    String(active)
                );
            });


        if (is3DMode) {
            instructions.innerHTML = `
                <strong>
                    Explora el producto
                </strong>

                <span>
                    Arrastra para girar. Usa dos dedos
                    o la rueda para acercar.
                </span>
            `;

            if (modelReady) {
                setViewerFeedback(
                    "Modelo listo. La vista actual se copiará a RA."
                );
            }
        } else {
            instructions.innerHTML = `
                <strong>
                    Ver en tu espacio
                </strong>

                <span>
                    La cámara usará el ángulo y acercamiento
                    actuales del Modelo 3D.
                </span>
            `;
        }


        panel.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
        });
    }


    open3DButton.addEventListener(
        "click",
        () => {
            showMode("3d");
        }
    );


    openARButton.addEventListener(
        "click",
        () => {
            showMode("ar");
        }
    );


    document
        .querySelectorAll("[data-mode]")
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    showMode(
                        button.dataset.mode
                    );
                }
            );
        });


    document
        .querySelectorAll("[data-view-rotate]")
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    rotateCamera(
                        Number(
                            button.dataset.viewRotate
                        )
                    );
                }
            );
        });


    const resetViewButton =
        document.querySelector(
            "[data-view-reset]"
        );


    if (resetViewButton) {
        resetViewButton.addEventListener(
            "click",
            resetCamera
        );
    }


    /*
     * Controles de giro dentro de WebXR.
     *
     * Parten de la vista copiada desde el Modelo 3D.
     */
    document
        .querySelectorAll("[data-ar-rotate]")
        .forEach((button) => {
            button.addEventListener(
                "click",
                (event) => {
                    event.stopPropagation();

                    arRotationY += Number(
                        button.dataset.arRotate
                    );

                    applyARTransformations();
                }
            );
        });


    document
        .querySelectorAll("[data-ar-scale]")
        .forEach((button) => {
            button.addEventListener(
                "click",
                (event) => {
                    event.stopPropagation();

                    arScale += Number(
                        button.dataset.arScale
                    );

                    applyARTransformations();
                }
            );
        });


    const resetARButton =
        document.querySelector(
            "[data-ar-reset]"
        );


    if (resetARButton) {
        resetARButton.addEventListener(
            "click",
            (event) => {
                event.stopPropagation();

                resetARTransformations();
            }
        );
    }


    launchARButton.addEventListener(
        "click",
        () => {
            setARMessage("");

            if (!modelReady) {
                setARMessage(
                    "El modelo todavía está cargando."
                );

                return;
            }

            if (!viewer.canActivateAR) {
                setARMessage(
                    "La realidad aumentada no está disponible " +
                    "en este dispositivo o navegador."
                );

                return;
            }


            const copiedSuccessfully =
                copyCurrent3DViewToAR();


            if (!copiedSuccessfully) {
                setARMessage(
                    "No fue posible obtener la vista actual " +
                    "del Modelo 3D."
                );

                return;
            }


            arLaunchInProgress = true;
            pageWasHiddenForAR = false;


            if (isIOS) {
                setARMessage(
                    "Preparando la vista y abriendo Quick Look…",
                    "information"
                );
            } else {
                setARMessage(
                    "Abriendo la cámara con la vista actual…",
                    "information"
                );
            }


            /*
             * activateAR debe ejecutarse directamente
             * durante el clic del usuario.
             */
            const result =
                viewer.activateAR();


            if (
                result
                && typeof result.catch === "function"
            ) {
                result.catch(() => {
                    restoreNormal3DViewer();

                    setARMessage(
                        "No fue posible abrir la cámara."
                    );
                });
            }
        }
    );


    viewer.addEventListener(
        "camera-change",
        () => {
            synchronizeCameraTheta();
        }
    );


    viewer.addEventListener(
        "ar-status",
        (event) => {
            const status =
                event.detail.status;


            if (status === "failed") {
                restoreNormal3DViewer();

                setARMessage(
                    "No fue posible iniciar la realidad aumentada."
                );
            }


            if (status === "session-started") {
                setARMessage(
                    "Mueve lentamente el teléfono y busca " +
                    "una superficie plana.",
                    "information"
                );
            }


            if (status === "object-placed") {
                setARMessage(
                    "Producto colocado con la vista del Modelo 3D.",
                    "success"
                );
            }


            if (status === "not-presenting") {
                restoreNormal3DViewer();

                setARMessage("");
            }
        }
    );


    viewer.addEventListener(
        "ar-tracking",
        (event) => {
            const trackingStatus =
                event.detail.status;


            if (trackingStatus === "not-tracking") {
                setARMessage(
                    "Mueve lentamente el teléfono y busca " +
                    "una zona con mejor iluminación.",
                    "information"
                );
            }


            if (trackingStatus === "tracking") {
                setARMessage("");
            }
        }
    );


    /*
     * Quick Look puede ocultar temporalmente Safari.
     * Al regresar restauramos solamente orientation y scale.
     * La órbita de la cámara 3D permanece donde el usuario la dejó.
     */
    document.addEventListener(
        "visibilitychange",
        () => {
            if (
                document.hidden
                && arLaunchInProgress
            ) {
                pageWasHiddenForAR = true;

                return;
            }


            if (
                !document.hidden
                && arLaunchInProgress
                && pageWasHiddenForAR
            ) {
                setTimeout(
                    restoreNormal3DViewer,
                    300
                );
            }
        }
    );


    /*
     * Preparación inicial.
     */
    setViewButtonsEnabled(false);
    launchARButton.disabled = true;

    renderDeviceInstructions();


    customElements
        .whenDefined("model-viewer")
        .then(() => {

            const finishLoading = () => {
                modelReady = true;

                setViewButtonsEnabled(true);

                resetCamera();

                setViewerFeedback(
                    "Modelo listo. La vista actual se copiará a RA."
                );


                /*
                 * canActivateAR puede actualizarse después
                 * de que termine la carga del GLB.
                 */
                const updateARAvailability = () => {
                    if (viewer.canActivateAR) {
                        launchARButton.disabled = false;

                        if (isIOS) {
                            setARMessage(
                                "El modelo está listo para abrirse " +
                                "en Quick Look.",
                                "success"
                            );
                        }

                        return;
                    }


                    launchARButton.disabled = true;


                    if (isMobile) {
                        setARMessage(
                            "Este dispositivo o navegador no pudo " +
                            "habilitar la realidad aumentada."
                        );
                    } else {
                        setARMessage(
                            "Abre esta página desde un teléfono " +
                            "compatible para utilizar RA.",
                            "information"
                        );
                    }
                };


                updateARAvailability();

                setTimeout(
                    updateARAvailability,
                    500
                );
            };


            if (viewer.loaded) {
                finishLoading();
            } else {
                viewer.addEventListener(
                    "load",
                    finishLoading,
                    {
                        once: true,
                    }
                );
            }
        });


    viewer.addEventListener(
        "error",
        () => {
            modelReady = false;

            setViewButtonsEnabled(false);
            launchARButton.disabled = true;

            setViewerFeedback(
                "No fue posible cargar el archivo 3D."
            );

            setARMessage(
                "Revisa que el archivo GLB sea válido."
            );
        }
    );
