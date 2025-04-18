document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".abstract-toggle").forEach(function (button) {
    button.addEventListener("click", function () {
      var abstract = button.nextElementSibling;
      if (abstract.style.display === "none" || !abstract.style.display) {
        abstract.style.display = "block";
      } else {
        abstract.style.display = "none";
      }
    });
  });
});
