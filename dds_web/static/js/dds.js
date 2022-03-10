// Validate form submissions nicely, using Bootstrap 5 validation classes.
(function () {
  "use strict";

  // Fetch all the forms we want to apply custom Bootstrap validation styles to
  var forms = document.querySelectorAll(".needs-validation");

  // Loop over them and prevent submission
  Array.prototype.slice.call(forms).forEach(function (form) {
    form.addEventListener(
      "submit",
      function (event) {
        form.classList.remove("failed-validation");
        if (!form.checkValidity()) {
          event.preventDefault();
          event.stopPropagation();
          form.classList.add("failed-validation");
        }
        form.classList.add("was-validated");
      },
      false
    );
  });
})();

//
// Dark mode switch
//

// OS set to dark mode
if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
  // Only continue if we have no cookie set
  if (document.cookie.indexOf("ddstheme") == -1) {
    // Set the dark mode switch to checked
    document.getElementById("theme-switcher-check").checked = true;
    document.getElementById("theme-switcher-sun").classList.add("d-none");
    document.getElementById("theme-switcher-moon").classList.remove("d-none");
  }
}
// OS theme changes (unlikely, but nice to support!)
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
  const newTheme = e.matches ? "dark" : "light";
  // Only continue if we have no cookie set
  if (document.cookie.indexOf("ddstheme") == -1) {
    // Set the dark mode switch
    if (newTheme == "dark") {
      document.getElementById("theme-switcher-check").checked = true;
      document.getElementById("theme-switcher-sun").classList.add("d-none");
      document.getElementById("theme-switcher-moon").classList.remove("d-none");
    } else {
      document.getElementById("theme-switcher-check").checked = false;
      document.getElementById("theme-switcher-sun").classList.remove("d-none");
      document.getElementById("theme-switcher-moon").classList.add("d-none");
    }
  }
});

// Manually set dark / light mode
document.querySelector(".theme-switcher").addEventListener("click", (e) => {
  const theme = document.getElementById("theme-switcher-check").checked ? "dark" : "light";
  // Change the CSS for the page
  var newlink = "/static/css/dds_" + theme + ".css";
  document.getElementById("dds-stylesheet").setAttribute("href", newlink);
  // Toggle the button
  document.getElementById("theme-switcher-check").checked = theme == "dark" ? true : false;
  document.getElementById("theme-switcher-sun").classList.toggle("d-none");
  document.getElementById("theme-switcher-moon").classList.toggle("d-none");
  // Set a cookie
  document.cookie = "ddstheme=" + theme + "; expires=Fri, 31 Dec 9999 23:59:59 GMT; path=/";
  console.log(document.cookie);
});

//
// Legacy jQuery code
//
$(function () {
  // Initialise Datatables
  $(".datatable").DataTable();
});
