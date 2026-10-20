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

    addOption(
      "__new_subcategory__",
      "+ Agregar nueva subcategoría"
    );

    const hasSubcategories =
      allowed.length > 0;
    const hasCategory = Boolean(category);

    // Incluso si una familia no tenía subcategorías,
    // permitir agregar una sin obligar a elegirla.
    subcategoryContainer.hidden = !hasCategory;
    subcategorySelect.disabled = !hasCategory;
    subcategorySelect.required = hasSubcategories;

    if (
      hasCategory &&
      (
        allowed.includes(previousValue) ||
        previousValue === "__new_subcategory__"
      )
    ) {
      subcategorySelect.value = previousValue;
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

  const newSubcategoryContainer =
    document.getElementById("new_subcategory_container");
  const newSubcategoryInput =
    document.getElementById("id_new_subcategory");

  function updateNewSubcategory() {
    if (!newSubcategoryContainer || !newSubcategoryInput) {
      return;
    }
    const isNew =
      subcategorySelect.value === "__new_subcategory__";
    newSubcategoryContainer.hidden = !isNew;
    newSubcategoryInput.disabled = !isNew;
    newSubcategoryInput.required = isNew;
  }

  subcategorySelect.addEventListener("change", updateNewSubcategory);
  categorySelect.addEventListener("change", updateNewSubcategory);

  updateSubcategories(true);
  updateNewSubcategory();

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