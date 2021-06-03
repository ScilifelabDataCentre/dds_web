// Validate form submissions nicely, using Bootstrap 5 validation classes.
(function () {
  'use strict'

  // Fetch all the forms we want to apply custom Bootstrap validation styles to
  var forms = document.querySelectorAll('.needs-validation')

  // Loop over them and prevent submission
  Array.prototype.slice.call(forms)
    .forEach(function (form) {
        form.addEventListener('submit', function (event) {
            form.classList.remove("failed-validation")
            if (!form.checkValidity()) {
                event.preventDefault()
                event.stopPropagation()
                form.classList.add("failed-validation")
            }
            form.classList.add('was-validated')
        }, false)
    })
})()

$(function () {

    // Initialise Datatables
    $('.datatable').DataTable();

});
