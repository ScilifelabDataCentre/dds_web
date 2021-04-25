/* Make project table sortable */
$('#sortTable').DataTable({ searching: false, info: false });

/* Submit upload by ajax so can have progress bar */
$('#data-upload-form').submit(function (e) {
    e.preventDefault();
    formElement = this;
    actionUrl = $(this).attr('action');
    requestMethod = $(this).attr('method');
    dataFromForm = new FormData(this);
    modalID = 'uploadModal-' + dataFromForm.get('project_id');
    jmodalID = '#' + modalID;
    // If modal doesn't exist, create and add event listener to refresh page
    if (!($(jmodalID).length)) {
        $('body').append(getModalHtml(modalID, "Upload in progress"));
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
            setUploadModalData(modalElement, "progress");
            modalElement.modal('show');
        },
        // function to execute on success
        success: function(resp){
            setUploadModalData(modalElement, "success", false);
        },
        // function to execute on failure
        error: function(err){
            setUploadModalData(modalElement, "error", false);
        },
        // function to execute always
        complete: function () {
            formElement.reset();
        }
    });
});

/* download related stuff */
$('span.li-dwn-box').html(`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-download" viewBox="0 0 16 16">
      <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
      <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
    </svg>
    `);

$('span.li-dwn-box').click(function(e){
    realForm = $('#data-download-form');
    file = getFileTree(this, '#uploaded-file-list');
    actionURL = realForm.attr('action');
    projectID = realForm.children('input[name="project_id"]').attr('value');
    submitDownloadForm(file, projectID, actionURL);
});

$( '#uploaded-file-list li' ).hover(
  function() {
    $( this ).find( 'span.li-dwn-box' ).first().css('visibility', 'visible');
  }, function() {
    $( this ).find( 'span.li-dwn-box' ).first().css('visibility', 'hidden');
  }
);

/* trail download by ajax, not implemented yet */
$('#download-butt').click(function(e) {
    buttonObj = $(this);
    $.ajax({
        url: buttonObj.data().action,
        method: 'POST',
        contentType: "application/json",
        data: JSON.stringify({'project_id' : buttonObj.data().project_id}),
        success: function(resp){
            console.log('success');
            alert(resp);
        }
    });
});

/* Give the modal design for request progress */
function getModalHtml(mId, mTitle) {
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
};

/* function to set the modal info */
function setUploadModalData(mElement, type, closeButtonDisabled=true){
    contentObject = {
        progress: {
            header: `
                <h5 class="modal-title">Update in progress</h5>
                <div class="spinner-border text-primary right-button-container"></div>
            `,
            body: `
                <div class="alert alert-info tcenter">
                    Data is being transferred to the server
                </div>
            `
        },
        success: {
            header: `
                <h5 class="modal-title">Update success</h5>
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="#42ba96" class="bi bi-check-circle" viewBox="0 0 16 16">
                  <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                  <path d="M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05z"/>
                </svg>
            `,
            body: `
                <div class="alert alert-success tcenter">
                    Data successfully transferred to server
                </div>
            `
        },
        error: {
            header: `
                <h5 class="modal-title">Update failed</h5>
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="#df4759" class="bi bi-x-circle" viewBox="0 0 16 16">
                  <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                  <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
                </svg>
            `,
            body: `
                <div class="alert alert-danger tcenter">
                    Data transfer failed on server side, contact DC
                </div>
            `
        }
    }

    mElement.find('#modalHeaderContent').html(contentObject[type].header);
    mElement.find('#modalBodyContent').html(contentObject[type].body);
    mElement.find('#closeModalButton').attr("disabled", closeButtonDisabled);

};

/* get file tree path for clicked entry */
function getFileTree(clickedObj, containerID){
    fileTree = [];
    $(clickedObj).parentsUntil(`${containerID} ul:first`).not('ul,div').each(function(i){
        fileTree.unshift($(this).find('.file,.folder').first().text());
    });
    return fileTree.join('/');
};

/* function to create form and submit for individual files */
function submitDownloadForm(file, projectID, actionURL){
    // remove old temp forms if any
    $('#temp-dwn-form').remove();
    formTemplate = `
        <form id="temp-dwn-form" method="POST" enctype="multipart/form-data", action="${actionURL}" autocomplete="off">
            <input type="hidden" name="project_id" value="${projectID}">
            <input type="hidden" name="data_path" value="${file}">
        </form>
    `;
    $('#download-form-container').append(formTemplate);
    $('#temp-dwn-form').submit()
};
