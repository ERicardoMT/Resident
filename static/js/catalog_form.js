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

    let subcategoriesByCategory = {};

  try {
    subcategoriesByCategory = JSON.parse(
      subcategorySelect.dataset
        .subcategoriesByCategory || "{}"
    );
  } catch (error) {
    console.error(
      "Error al cargar las subcategorías:",
      error
    );
  }

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

    const newCategoryContainer =
    document.getElementById("new_category_container");

  const newCategoryInput =
    document.getElementById("id_new_category");

  if (newCategoryContainer && newCategoryInput) {
    function updateNewCategory() {
      const isNew =
        categorySelect.value === "__new_category__";

      newCategoryContainer.hidden = !isNew;
      newCategoryInput.required = isNew;
      newCategoryInput.disabled = !isNew;
    }

    categorySelect.addEventListener(
      "change",
      updateNewCategory
    );

    updateNewCategory();
  }
})();