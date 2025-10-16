let currentDownloadId = null;
let statusCheckInterval = null;

function startDownload() {
    const urlInput = document.getElementById('teraboxUrl');
    const url = urlInput.value.trim();
    
    if (!url) {
        alert('Please enter a TeraBox URL');
        return;
    }
    
    // Validate URL
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        alert('Please enter a valid URL starting with http:// or https://');
        return;
    }
    
    // Disable button and show loading
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.disabled = true;
    downloadBtn.textContent = 'Processing...';
    
    // Show status container
    const statusContainer = document.getElementById('statusContainer');
    statusContainer.classList.remove('hidden');
    
    // Reset status
    updateStatus('processing', 'Initializing download...');
    hideError();
    hideActionButtons();
    
    // Start download process
    fetch('/download', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        currentDownloadId = data.download_id;
        startStatusChecking();
    })
    .catch(error => {
        showError(error.message);
        resetDownloadButton();
    });
}

function startStatusChecking() {
    // Clear existing interval
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    // Check status every 2 seconds
    statusCheckInterval = setInterval(() => {
        checkStatus();
    }, 2000);
}

function checkStatus() {
    if (!currentDownloadId) return;
    
    fetch(`/status/${currentDownloadId}`)
        .then(response => response.json())
        .then(status => {
            updateUI(status);
            
            // Stop checking if completed or error
            if (status.status === 'completed' || status.status === 'error') {
                clearInterval(statusCheckInterval);
                resetDownloadButton();
            }
        })
        .catch(error => {
            console.error('Error checking status:', error);
        });
}

function updateUI(status) {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusMessage = document.getElementById('statusMessage');
    const progressInfo = document.getElementById('progressInfo');
    const fileInfo = document.getElementById('fileInfo');
    
    // Update status indicator and message
    statusIndicator.className = `status-indicator ${status.status}`;
    statusMessage.textContent = status.message;
    
    // Update file info
    if (status.filename) {
        fileInfo.textContent = `File: ${status.filename}`;
        fileInfo.style.display = 'block';
    } else {
        fileInfo.style.display = 'none';
    }
    
    // Update progress info
    if (status.file_size) {
        const sizeMB = (status.file_size / (1024 * 1024)).toFixed(2);
        progressInfo.textContent = `Size: ${sizeMB} MB`;
        progressInfo.style.display = 'block';
    } else {
        progressInfo.style.display = 'none';
    }
    
    // Show appropriate buttons
    if (status.status === 'completed') {
        showActionButtons();
    } else if (status.status === 'error') {
        showError(status.message);
        showNewDownloadButton();
    }
}

function updateStatus(status, message) {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusMessage = document.getElementById('statusMessage');
    
    statusIndicator.className = `status-indicator ${status}`;
    statusMessage.textContent = message;
}

function downloadFile() {
    if (!currentDownloadId) return;
    
    window.location.href = `/download-file/${currentDownloadId}`;
}

function newDownload() {
    // Reset everything
    currentDownloadId = null;
    
    // Clear URL input
    document.getElementById('teraboxUrl').value = '';
    
    // Hide status container
    document.getElementById('statusContainer').classList.add('hidden');
    
    // Reset download button
    resetDownloadButton();
    
    // Hide error and action buttons
    hideError();
    hideActionButtons();
}

function showActionButtons() {
    const actionButtons = document.getElementById('actionButtons');
    actionButtons.classList.remove('hidden');
}

function hideActionButtons() {
    const actionButtons = document.getElementById('actionButtons');
    actionButtons.classList.add('hidden');
}

function showNewDownloadButton() {
    const actionButtons = document.getElementById('actionButtons');
    actionButtons.classList.remove('hidden');
    document.getElementById('downloadFileBtn').style.display = 'none';
    document.getElementById('newDownloadBtn').style.display = 'block';
}

function showError(message) {
    const errorElement = document.getElementById('errorMessage');
    errorElement.textContent = message;
    errorElement.classList.remove('hidden');
}

function hideError() {
    const errorElement = document.getElementById('errorMessage');
    errorElement.classList.add('hidden');
}

function resetDownloadButton() {
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.disabled = false;
    downloadBtn.textContent = 'Download File';
}

// Enter key support
document.getElementById('teraboxUrl').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        startDownload();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    hideError();
    hideActionButtons();
});