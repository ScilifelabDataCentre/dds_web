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

    // Submit upload by ajax so can have progress bar
    $('#data-upload-form').submit(function (e) {
        e.preventDefault();
        dataForModal = {
            progress: {
                head: "Upload in progress",
                body: "Data is being transferred to S3"
            },
            success: "Upload success",
            error: "Upload failed"
        };
        submitWithModel(this, 'uploadModal-' + $(this).find('input[name="project_id"]').prop("value"), dataForModal);
    });

    /*  FUNCTIONS USED  */

    /* To submit a form request with progress modal */
    function submitWithModel(form, modalID, mCnt){
        formElement = form;
        actionUrl = $(form).attr('action');
        requestMethod = $(form).attr('method');
        dataFromForm = new FormData(form);
        jmodalID = '#' + modalID;
        // If modal doesn't exist, create and add event listener to refresh page
        if (!($(jmodalID).length)) {
            $('body').append(getModalHtml(modalID));
            $(jmodalID).on('hidden.bs.modal', function () { location.reload(); });
        }
        modalElement = $(jmodalID);
        $.ajax({
            url: actionUrl,
            method: requestMethod,
            data: dataFromForm,
            processData: false,
            contentType: false,
            // function to execute before request
            beforeSend: function(){
                setModalData(modalElement, "progress", mCnt.progress.head, mCnt.progress.body, true);
                modalElement.modal('show');
            },
            // function to execute on success
            success: function(resp){
                setModalData(modalElement, "success", mCnt.success, resp.message, false);
            },
            // function to execute on failure
            error: function(err){
                console.log(err);
                if (err.status == 413) {
                    uLimit = $(formElement).find('input[name="upload_limit"]').prop("value");
                    eMsg = `Data size greater upload threshold (${uLimit}), cannot upload`;
                } else {
                    eMsg = err.responseJSON.message;
                }
                setModalData(modalElement, "error", mCnt.error, eMsg, false);
            },
            // function to execute always
            complete: function () {
                formElement.reset();
            }
        });
    }

    /* Give the modal design for request progress */
    function getModalHtml(mId) {
        modalHTMLTemplate = `
            <div class="modal fade" id="${mId}" data-backdrop="static" data-keyboard="false" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                <div class="modal-header" id="modalHeaderContent">
                </div>
                <div class="modal-body" id="modalBodyContent">
                </div>
                <div class="modal-footer">
                    <button id="closeModalButton" type="button" class="btn btn-light border btn-sm mx-auto" data-dismiss="modal">Close</button>
                </div>
                </div>
            </div>
            </div>
        `;
        return modalHTMLTemplate;
    };

    /* function to set the modal info */
    function setModalData(mElement, type, head, body, closeButtonDisabled=true,){

        if (type == 'progress'){
            mhead = `
                    <h5 class="modal-title">${head}</h5>
                    <div class="spinner-border text-primary right-button-container"></div>
                    `;
            mbody = `
                    <div class="alert alert-info tcenter">
                        ${body}
                    </div>
                    `;
        } else if (type == 'success'){
            mhead = `
                    <h5 class="modal-title">${head}</h5>
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="#42ba96" class="bi bi-check-circle" viewBox="0 0 16 16">
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                    <path d="M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05z"/>
                    </svg>
                    `;
            mbody = `
                    <div class="alert alert-success tcenter">
                        ${body}
                    </div>
                    `;
        } else if (type == 'error'){
            mhead =  `
                    <h5 class="modal-title">${head}</h5>
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="#df4759" class="bi bi-x-circle" viewBox="0 0 16 16">
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                    <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
                    </svg>
                    `;
            mbody = `
                    <div class="alert alert-danger tcenter">
                        ${body}
                    </div>
                    `;
        };

        mElement.find('#modalHeaderContent').html(mhead);
        mElement.find('#modalBodyContent').html(mbody);
        mElement.find('#closeModalButton').attr("disabled", closeButtonDisabled);
    };

});
