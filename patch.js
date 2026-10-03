function updateUndoButton() {
    undoButton.disabled = undoDrafts.length === 0 && !savedUndoAvailable;
    
    var saveBtn = document.getElementById('sellerSaveButton');
    if (saveBtn) {
        saveBtn.disabled = undoDrafts.length === 0;
        saveBtn.innerHTML = '&#x1F4BE; Save changes (' + undoDrafts.length + ')';
    }
}
