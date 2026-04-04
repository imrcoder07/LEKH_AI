﻿let selectedFile = null;

function toggleLanguage() {
    fetch('/api/lang/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            window.location.reload();
        }
    })
    .catch(error => console.error('Error toggling language:', error));
}

function isHindi() {
    return document.documentElement.lang === 'hi';
}

function resetUploadState() {
    selectedFile = null;
    document.getElementById('drop-zone').classList.remove('hidden');
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('result-state').classList.add('hidden');
    document.getElementById('upload-footer').classList.remove('hidden');
    document.getElementById('file-meta').classList.add('hidden');
    document.getElementById('file-meta').innerHTML = '';
    document.getElementById('upload-text').innerText = isHindi()
        ? 'यहाँ भूमि रिकॉर्ड छोड़ें या चुनने के लिए क्लिक करें'
        : 'Drop a land record here or click to choose';
    document.getElementById('file-input').value = '';
}

function openDpdpModal() {
    document.getElementById('dpdp-modal').classList.add('active');
    document.getElementById('dpdp-modal').setAttribute('aria-hidden', 'false');
    document.getElementById('dpdp-consent-checkbox').checked = false;
    document.getElementById('btn-proceed').disabled = true;
}

function closeModals() {
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
    });
    resetUploadState();
}

function proceedToUpload() {
    document.getElementById('dpdp-modal').classList.remove('active');
    document.getElementById('dpdp-modal').setAttribute('aria-hidden', 'true');
    setTimeout(() => {
        document.getElementById('upload-modal').classList.add('active');
        document.getElementById('upload-modal').setAttribute('aria-hidden', 'false');
    }, 160);
}

function preventDefaults(event) {
    event.preventDefault();
    event.stopPropagation();
}

function humanFileSize(bytes) {
    if (!bytes && bytes !== 0) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let index = 0;
    while (size >= 1024 && index < units.length - 1) {
        size /= 1024;
        index += 1;
    }
    return `${size.toFixed(size >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function updateFileMeta(file) {
    const meta = document.getElementById('file-meta');
    const type = file.type || (isHindi() ? 'अज्ञात प्रकार' : 'Unknown type');
    meta.innerHTML = `
        <strong>${isHindi() ? 'चयनित फ़ाइल' : 'Selected file'}</strong><br>
        ${file.name}<br>
        ${isHindi() ? 'आकार' : 'Size'}: ${humanFileSize(file.size)}<br>
        ${isHindi() ? 'प्रकार' : 'Type'}: ${type}
    `;
    meta.classList.remove('hidden');
}

function handleFiles(files) {
    if (!files || files.length === 0) return;
    selectedFile = files[0];
    document.getElementById('upload-text').innerText = selectedFile.name;
    updateFileMeta(selectedFile);
}

function submitUpload() {
    if (!selectedFile) {
        alert(isHindi() ? 'कृपया पहले एक फ़ाइल चुनें।' : 'Please choose a file first.');
        return;
    }

    document.getElementById('drop-zone').classList.add('hidden');
    document.getElementById('upload-footer').classList.add('hidden');
    document.getElementById('loading-state').classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', selectedFile);

    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => showResult(data))
    .catch(error => {
        console.error('Upload error:', error);
        showResult({
            status: 'error',
            message: isHindi() ? 'अपलोड के दौरान नेटवर्क समस्या उत्पन्न हुई।' : 'A network problem occurred during upload.'
        });
    });
}

function showResult(data) {
    document.getElementById('loading-state').classList.add('hidden');

    const resultState = document.getElementById('result-state');
    const resultTitle = document.getElementById('result-title');
    const resultIcon = document.getElementById('result-icon');
    const resultDetails = document.getElementById('result-details');

    resultState.classList.remove('hidden');

    let iconSvg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#002103" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
    let titleColor = 'var(--success-ink)';
    let titleText = isHindi() ? 'अपलोड सफल' : 'Upload Successful';
    let summary = data.message || (isHindi() ? 'दस्तावेज़ सफलतापूर्वक संसाधित किया गया।' : 'Document processed successfully.');

    const aadhaarFound = data.data ? data.data.aadhaar_found : data.aadhaar_found;
    if (data.status === 'success' && aadhaarFound === false) {
        titleText = isHindi() ? 'विरासत रिकॉर्ड संग्रहीत' : 'Legacy Record Stored';
    } else if (data.status === 'flagged') {
        iconSvg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ba1a1a" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>';
        titleColor = 'var(--danger)';
        titleText = isHindi() ? 'मैनुअल समीक्षा आवश्यक' : 'Manual Review Required';
        summary = data.message || (isHindi() ? 'भंडारण से पहले इस दस्तावेज़ की मैन्युअल समीक्षा की आवश्यकता है।' : 'This document needs manual review before storage.');
    } else if (data.status === 'exists') {
        titleText = isHindi() ? 'रिकॉर्ड पहले से मौजूद है' : 'Record Already Exists';
        summary = data.message || (isHindi() ? 'इस ULPIN का रिकॉर्ड डेटाबेस में पहले से मौजूद है।' : 'A record for this ULPIN is already present in the database.');
    } else if (data.status === 'error') {
        iconSvg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ba1a1a" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
        titleColor = 'var(--danger)';
        titleText = isHindi() ? 'अपलोड त्रुटि' : 'Upload Error';
        summary = data.message || (isHindi() ? 'दस्तावेज़ संसाधित करते समय कुछ गलत हो गया।' : 'Something went wrong while processing the document.');
    }

    resultIcon.innerHTML = iconSvg;
    resultTitle.innerText = titleText;
    resultTitle.style.color = titleColor;
    resultDetails.innerText = `${summary}\n\n${JSON.stringify(data, null, 2)}`;
}

document.addEventListener('DOMContentLoaded', () => {
    const consentBox = document.getElementById('dpdp-consent-checkbox');
    const proceedBtn = document.getElementById('btn-proceed');
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

        if (consentBox && proceedBtn) {
            consentBox.addEventListener('change', event => {
                proceedBtn.disabled = !event.target.checked;
            });
        }

    // Auto-run verification on dashboard load
    if (window.location.pathname === '/dashboard') {
        runVerification();
    }
    });
        

function runVerification() {
    const statusEl = document.getElementById('verification-status');
    const resultContainer = document.getElementById('verification-result');

    if (statusEl) {
        statusEl.innerHTML = isHindi() ? 'सत्यापन चल रहा है...' : 'Running verification...';
    }

    fetch('/api/verify')
        .then(response => response.json())
        .then(data => {
            if (!resultContainer) return;
            if (data.status === 'INTACT') {
                resultContainer.innerHTML = `<div style="color: var(--success-ink);">
                    <h3>${isHindi() ? '✅ लेजर सुरक्षित और अपरिवर्तित है' : '✅ Ledger Intact & Verified'}</h3>
                    <p>${isHindi() ? 'सभी क्रिप्टोग्राफ़िक हैश मान्य हैं। किसी भी रिकॉर्ड में कोई छेड़छाड़ नहीं पाई गई है।' : 'All cryptographic hashes are valid. No tampering has been detected in any record.'}</p>
                </div>`;
            } else if (data.status === 'EMPTY') {
                resultContainer.innerHTML = `<div>
                    <h3>${isHindi() ? 'ℹ️ लेजर खाली है' : 'ℹ️ Ledger Empty'}</h3>
                    <p>${isHindi() ? 'सिस्टम में अभी तक कोई रिकॉर्ड दर्ज नहीं किया गया है।' : 'No records have been ingested into the system yet.'}</p>
                </div>`;
            } else {
                resultContainer.innerHTML = `<div style="color: var(--danger);">
                    <h3>${isHindi() ? '❌ छेड़छाड़ पाई गई!' : '❌ Tampering Detected!'}</h3>
                    <p>${isHindi() ? 'चेतावनी: लेजर हैश मेल नहीं खाते। डेटा की अखंडता से समझौता किया गया है।' : 'WARNING: Ledger hashes do not match. Data integrity has been compromised.'}</p>
                    <pre>${JSON.stringify(data.details || data, null, 2)}</pre>
                </div>`;
            }
            if (statusEl) statusEl.innerHTML = '';
        })
        .catch(error => {
            console.error('Verification error:', error);
            if (statusEl) {
                statusEl.innerHTML = `<span style="color: var(--danger);">${isHindi() ? 'सत्यापन विफल रहा।' : 'Verification failed.'}</span>`;
            }
        });
}