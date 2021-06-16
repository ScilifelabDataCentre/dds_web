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

    // Function to switch CSS theme file
    $('.theme-switcher').click(function (e) {
        var theme = $('#theme-switcher-check').prop('checked') ? 'dark' : 'light';

        // Switch the stylesheet
        var newlink = '/static/css/dds_' + theme + '.css';
        $('#dds-stylesheet').attr('href', newlink);

        // Toggle the button
        $('.theme-switcher label i, .theme-switcher label svg').toggleClass('d-none');

        // Set a cookie to remember
        document.cookie = 'ddstheme=' + theme + '; expires=Thu, 2 Dec 2032 12:00:00 UTC; path=/';
    });

});
