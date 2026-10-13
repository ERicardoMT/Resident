(function () {
  "use strict";


  function normalizeText(value) {
    return (value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/:$/, "");
  }


  // =====================================================
  // FICHA NORMAL DE PRODUCTO
  // =====================================================

  function cleanProductDescription() {

    const detail =
      document.querySelector(
        ".product-description"
      );


    if (!detail) {
      return;
    }


    const hiddenFields =
      new Set([
        "3d",
        "revisar",
        "precio web",
        "precio web (mas iva)",
      ]);


    detail
      .querySelectorAll(
        "table tr"
      )
      .forEach(
        function (row) {

          if (!row.cells.length) {
            return;
          }


          const firstCell =
            row.cells[0];


          const label =
            normalizeText(
              firstCell.textContent
            );


          if (
            label ===
            "nombre comercial (web)"
          ) {

            firstCell.textContent =
              "Nombre comercial";

          }


          if (
            row.cells.length === 2
            &&
            hiddenFields.has(
              label
            )
          ) {

            row.remove();

          }

        }
      );

  }


  // =====================================================
  // BASE Y ALTURA PARA VISOR 3D / AR
  // =====================================================

  function populateProductMeasurements() {

    const source =
      document.getElementById(
        "smav-ficha-accionamiento"
      );


    if (!source) {
      return;
    }


    let html = "";


    try {

      html =
        JSON.parse(
          source.textContent
        );

    } catch (error) {

      return;

    }


    const documentFromDescription =
      new DOMParser()
        .parseFromString(
          html || "",
          "text/html"
        );


    const fieldAliases = {

      base: [
        "base",
        "diametro de base",
        "ancho de base",
        "ancho de caja",
      ],

      altura: [
        "altura",
        "altura total",
        "altura de base",
        "alto",
      ],

    };


    const values = {};


    documentFromDescription
      .querySelectorAll(
        "table tr"
      )
      .forEach(
        function (row) {

          const cells =
            row.cells;


          if (
            cells.length !== 2
          ) {

            return;

          }


          const name =
            normalizeText(
              cells[0]
                .textContent
            )
              .replace(
                /\s*\([^)]*\)$/,
                ""
              );


          Object
            .entries(
              fieldAliases
            )
            .forEach(
              function (
                [kind, aliases]
              ) {

                if (
                  values[kind]
                  ||
                  !aliases.includes(
                    name
                  )
                ) {

                  return;

                }


                const value =
                  cells[1]
                    .textContent
                    .trim();


                if (
                  value
                  &&
                  value !== "-"
                ) {

                  values[kind] =
                    value;

                }

              }
            );

        }
      );


    ["base", "altura"]
      .forEach(
        function (kind) {

          const label =
            document.querySelector(
              `[data-smav-medida="${kind}"]`
            );


          if (!label) {
            return;
          }


          const title =
            kind === "base"
              ? "Base"
              : "Altura";


          label.textContent =
            title
            + ": "
            + (
              values[kind]
              || "No especificada"
            );

        }
      );

  }


  cleanProductDescription();

  populateProductMeasurements();

})();