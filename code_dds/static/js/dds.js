$('#sortTable').DataTable({searching: false, info: false});

$('#data-upload-form').submit(function(e) {
    e.preventDefault();
    formElement = this;
    actionUrl = $(this).attr('action');
    requestMethod = $(this).attr('method');
    dataFromForm = new FormData(this);
    modalID = 'uploadModal-' + dataFromForm.get('project_id');
    jmodalID = '#' + modalID;
    // If modal doesn't exist, create and add event listener to refresh page
    if (!($(jmodalID).length)){
        $('body').append(getModalHtml(modalID, "Upload in progress"));
        $(jmodalID).on('hidden.bs.modal', function(){ location.reload(); });
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
            setModalData(modalElement, "progress");
            modalElement.modal('show');
        },
        // function to execute on success
        success: function(resp){
            setModalData(modalElement, "success", false);
        },
        // function to execute on failure
        error: function(err){
            setModalData(modalElement, "error", false);
        },
        // function to execute always
        complete: function(){
            formElement.reset();
        }
    });
});


function getModalHtml(mId, mTitle){
    modalHTMLTemplate = `
        <div class="modal fade" id="${mId}" data-backdrop="static" data-keyboard="false" tabindex="-1" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-header" id="modalHeaderContent">
              </div>
              <div class="modal-body" id="modalBodyContent">
              </div>
              <div class="modal-footer">
                <button id="closeModalButton" type="button" class="btn btn-secondary btn-sm mx-auto" data-dismiss="modal">close</button>
              </div>
            </div>
          </div>
        </div>
    `;
    return modalHTMLTemplate;
}


function setModalData(mElement, type, closeButtonDisabled=true){
    contentObject = {
        progress : {
            header : `
                <h5 class="modal-title">Update in progress</h5>
                <div class="spinner-border text-primary right-button-container"></div>
            `,
            body : `
                <div class="alert alert-info tcenter">
                    Data is being transferred to the server
                </div>
            `
        },
        success : {
            header : `
                <h5 class="modal-title">Update success</h5>
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="#42ba96" class="bi bi-check-circle" viewBox="0 0 16 16">
                  <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                  <path d="M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05z"/>
                </svg>
            `,
            body : `
                <div class="alert alert-success tcenter">
                    Data successfully transferred to server
                </div>
            `
        },
        error : {
            header : `
                <h5 class="modal-title">Update failed</h5>
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="#df4759" class="bi bi-x-circle" viewBox="0 0 16 16">
                  <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                  <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
                </svg>
            `,
            body : `
                <div class="alert alert-danger tcenter">
                    Data transfer failed on server side, contact DC
                </div>
            `
        }
    }

    mElement.find('#modalHeaderContent').html(contentObject[type].header);
    mElement.find('#modalBodyContent').html(contentObject[type].body);
    mElement.find('#closeModalButton').attr("disabled", closeButtonDisabled);
    
}

