(function () {
  "use strict";

  var input =
    document.getElementById(
      "ar-model-search-input"
    );

  var results =
    document.getElementById(
      "ar-model-search-results"
    );

  var empty =
    document.getElementById(
      "ar-model-search-empty"
    );

  var items =
    Array.from(
      document.querySelectorAll(
        "[data-ar-search-item]"
      )
    );


  if (
    !input
    ||
    !results
  ) {
    return;
  }


  function normalizeText(value) {

    return String(
      value || ""
    )
      .normalize("NFD")
      .replace(
        /[\u0300-\u036f]/g,
        ""
      )
      .toLowerCase()
      .trim();

  }


  function hideResults() {

    results.hidden =
      true;

    items.forEach(
      function (item) {

        item.hidden =
          true;

      }
    );

    if (empty) {

      empty.hidden =
        true;

    }

  }


  function updateResults() {

    var query =
      normalizeText(
        input.value
      );


    if (!query) {

      hideResults();

      return;

    }


    var matches =
      items.filter(
        function (item) {

          var searchableText =
            normalizeText(
              item.getAttribute(
                "data-search-text"
              )
            );

          return searchableText.includes(
            query
          );

        }
      );


    /*
     * Mostramos máximo 8 resultados
     * para no llenar toda la pantalla.
     */
    var visibleMatches =
      matches.slice(
        0,
        8
      );


    items.forEach(
      function (item) {

        item.hidden =
          true;

      }
    );


    visibleMatches.forEach(
      function (item) {

        item.hidden =
          false;

      }
    );


    results.hidden =
      false;


    if (empty) {

      empty.hidden =
        visibleMatches.length > 0;

    }

  }


  input.addEventListener(
    "input",
    updateResults
  );


  input.addEventListener(
    "keydown",
    function (event) {

      if (
        event.key === "Escape"
      ) {

        input.value =
          "";

        hideResults();

        input.blur();

      }

    }
  );


  document.addEventListener(
    "click",
    function (event) {

      var searchSection =
        input.closest(
          ".ar-model-search"
        );

      if (
        searchSection
        &&
        !searchSection.contains(
          event.target
        )
      ) {

        hideResults();

      }

    }
  );

})();
