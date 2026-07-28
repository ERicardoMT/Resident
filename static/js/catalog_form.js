(function () {
  "use strict";

  const categorySelect =
    document.getElementById("id_category");

  const subcategorySelect =
    document.getElementById("id_subcategory");

  const subcategoryContainer =
    document.getElementById(
      "subcategory_container"
    );

  if (
    !categorySelect ||
    !subcategorySelect ||
    !subcategoryContainer
  ) {
    return;
  }

  const subcategoriesByCategory = {
    antivibratorios: [
      "colgantes",
      "niveladores_maq",
      "pies",
      "soportes_piso",
      "tacones",
    ],

    patas_niveladoras: [
      "alta_resistencia",
      "anclaje_piso",
      "antiderrapante",
      "antivibracion",
      "con_rotula",
      "uso_rudo",
    ],

    accionamiento: [],
    mobiliario: [],
  };

  const labels = {};

  Array.from(
    subcategorySelect.options
  ).forEach(function (option) {
    labels[option.value] =
      option.textContent;
  });

  const initialSubcategory =
    subcategorySelect.value;

  function addOption(value, label) {
    const option =
      document.createElement("option");

    option.value = value;
    option.textContent = label;

    subcategorySelect.appendChild(option);
  }

  function updateSubcategories(
    preserveValue
  ) {
    const category =
      categorySelect.value;

    const allowed =
      subcategoriesByCategory[category]
      || [];

    const previousValue =
      preserveValue
        ? (
            subcategorySelect.value
            || initialSubcategory
          )
        : "";

    subcategorySelect.innerHTML = "";

    addOption(
      "",
      "Selecciona una subcategoría"
    );

    allowed.forEach(function (value) {
      addOption(
        value,
        labels[value] || value
      );
    });

    const hasSubcategories =
      allowed.length > 0;

    subcategoryContainer.hidden =
      !hasSubcategories;

    subcategorySelect.disabled =
      !hasSubcategories;

    subcategorySelect.required =
      hasSubcategories;

    if (
      hasSubcategories &&
      allowed.includes(previousValue)
    ) {
      subcategorySelect.value =
        previousValue;
    } else {
      subcategorySelect.value = "";
    }
  }

  categorySelect.addEventListener(
    "change",
    function () {
      updateSubcategories(false);
    }
  );

  updateSubcategories(true);
})();