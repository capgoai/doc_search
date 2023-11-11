document.getElementById('uploadForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const fileInput = document.getElementById('file');
    const file = fileInput.files[0];
    uploadFile(file).then(response => {
        if (response.ok) {
            listDocuments();
        } else {
            alert('Upload failed');
        }
    }).catch(error => {
        console.error('Error:', error);
        alert('Upload failed with an error');
    });
});

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('http://localhost:8000/v1/sources/add-file', {
        method: 'POST',
        headers: { 'x-api-key': 'sk_IzQFuUxkIx' },
        body: formData
    });
    return response;
}

let currentDocuments = []; // Global variable to store the documents


async function listDocuments() {
    const response = await fetch('http://localhost:8000/v1/uploaded?page=1&page_size=10', {
        method: 'GET',
        headers: { 'x-api-key': 'sk_IzQFuUxkIx' }
    });
    const data = await response.json();

    if (data.documents && data.documents.length > 0) {
        currentDocuments = data.documents; // Store the documents in the global variable

        updateDocumentTable(data.documents);
    } else {
        displayNoDocumentsMessage();
    }
}


function updateDocumentTable(documents) {
    let tableHtml = `
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Size</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">State</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created At</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">`;

    documents.forEach(doc => {
        const formattedSize = formatFileSize(doc.file_size);
        const formattedDate = formatDate(doc.create_at);
        const wrappedName = wrapText(doc.doc_name, 30); // Assuming max 30 characters per line
        tableHtml += `
            <tr>
                <td class="px-6 py-4 whitespace-nowrap">${doc.doc_id}</td>
                <td class="px-6 py-4 whitespace-normal">${wrappedName}</td>
                <td class="px-6 py-4 whitespace-nowrap">${doc.doc_type}</td>
                <td class="px-6 py-4 whitespace-nowrap">${formattedSize}</td>
                <td class="px-6 py-4 whitespace-nowrap">${doc.state}</td>
                <td class="px-6 py-4 whitespace-nowrap">${formattedDate}</td>
            </tr>`;
    });

    tableHtml += `</tbody></table>`;
    document.getElementById('documentTable').innerHTML = tableHtml;
}

function formatFileSize(size) {
    const units = ['bytes', 'KB', 'MB', 'GB', 'TB'];
    let index = 0;
    while (size >= 1024 && index < units.length - 1) {
        size /= 1024;
        index++;
    }
    return size.toFixed(2) + ' ' + units[index];
}

function formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString();
}

function wrapText(text, maxLineLength) {
    const words = text.split(' ');
    let wrappedText = '';
    let currentLineLength = 0;

    words.forEach(word => {
        if (currentLineLength + word.length > maxLineLength) {
            wrappedText += '\n'; // Start a new line
            currentLineLength = 0;
        }
        wrappedText += word + ' ';
        currentLineLength += word.length + 1; // Include space
    });

    return wrappedText.trim().replace(/\n/g, '<br>'); // Replace newline characters with HTML line breaks
}

function displayNoDocumentsMessage() {
    document.getElementById('documentTable').innerHTML = "<div class='text-center text-gray-500 mt-4'>No documents available.</div>";
}



function downloadCSV() {
    if (!currentDocuments || currentDocuments.length === 0) {
        alert('No documents to download.');
        return;
    }
    let csvContent = "data:text/csv;charset=utf-8,";

    // CSV Header
    csvContent += "ID,Name,Type,Size,State,Created At\r\n";

    // Adding each row of data
    currentDocuments.forEach(doc => {
        const row = [
            doc.doc_id,
            `"${doc.doc_name.replace(/"/g, '""')}"`, // Handle quotes in data
            doc.doc_type,
            formatFileSize(doc.file_size),
            doc.state,
            formatDateForCSV(doc.create_at)
        ].join(",");
        csvContent += row + "\r\n";
    });

    // Create a link and trigger download
    var encodedUri = encodeURI(csvContent);
    var link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "documents.csv");
    document.body.appendChild(link); // Required for Firefox
    link.click();
    document.body.removeChild(link);
}

function formatDateForCSV(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Triggering the download
document.getElementById('downloadCsvBtn').addEventListener('click', function() {
    listDocuments().then(documents => {
        downloadCSV(documents);
    });
});

document.getElementById('copyIdsBtn').addEventListener('click', function() {
    copyDocumentIDs();
});

function copyDocumentIDs() {
    if (!currentDocuments || currentDocuments.length === 0) {
        alert('No documents available to copy.');
        return;
    }

    const ids = currentDocuments.map(doc => doc.doc_id).join('\n');
    navigator.clipboard.writeText(ids).then(function() {
        alert('Document IDs copied to clipboard.');
    }, function(err) {
        alert('Failed to copy document IDs. Clipboard access may be restricted on non-HTTPS sites.');
        console.error('Clipboard Error:', err);
    });
}
