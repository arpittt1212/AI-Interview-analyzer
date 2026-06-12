// main.js - Core interactive behaviors for AI Interview Analyzer

document.addEventListener('DOMContentLoaded', () => {
    initDragAndDrop();
    initTranscriptHighlight();
    initProcessingConsole();
});

// 1. Drag and Drop File Upload Handler
function initDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileDetails = document.getElementById('file-details');
    const fileNameEl = document.getElementById('file-name');
    const fileSizeEl = document.getElementById('file-size');
    const uploadProgressContainer = document.getElementById('upload-progress-container');
    const uploadProgressBar = document.getElementById('upload-progress-bar');
    const uploadProgressPercent = document.getElementById('upload-progress-percent');
    const startAnalysisBtn = document.getElementById('start-analysis-btn');
    const uploadForm = document.getElementById('upload-form');

    if (!dropZone || !fileInput) return;

    // Trigger click on file input when dropzone is clicked
    dropZone.addEventListener('click', () => fileInput.click());

    // Highlight drop zone on dragover
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        }, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelection(files[0]);
        }
    });

    // Handle file selection from dialog
    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length > 0) {
            handleFileSelection(fileInput.files[0]);
        }
    });

    function handleFileSelection(file) {
        // Show file details card
        fileNameEl.textContent = file.name;
        fileSizeEl.textContent = formatBytes(file.size);
        fileDetails.style.display = 'flex';
        
        // Enable Start button
        startAnalysisBtn.disabled = false;
    }

    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    // Handle Upload Submission & Progress Bar Simulation
    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            // Disable start button
            startAnalysisBtn.disabled = true;
            
            // Show progress container
            uploadProgressContainer.style.display = 'block';
            
            // Perform AJAX Upload
            const formData = new FormData(uploadForm);
            const xhr = new XMLHttpRequest();
            
            xhr.open('POST', '/upload', true);
            
            // Update progress bar
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const percentComplete = Math.round((event.loaded / event.total) * 100);
                    uploadProgressBar.style.width = percentComplete + '%';
                    uploadProgressPercent.textContent = percentComplete + '%';
                }
            });
            
            xhr.onload = function() {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success && response.redirect) {
                        window.location.href = response.redirect;
                    } else {
                        alert('Upload failed: ' + (response.error || 'Unknown error'));
                        startAnalysisBtn.disabled = false;
                        uploadProgressContainer.style.display = 'none';
                    }
                } else {
                    alert('An error occurred during file upload.');
                    startAnalysisBtn.disabled = false;
                    uploadProgressContainer.style.display = 'none';
                }
            };
            
            xhr.onerror = function() {
                alert('Upload error occurred.');
                startAnalysisBtn.disabled = false;
                uploadProgressContainer.style.display = 'none';
            };
            
            xhr.send(formData);
        });
    }
}

// 2. Real-time Processing Stage Console Handler
function initProcessingConsole() {
    const processingWrapper = document.getElementById('processing-console-wrapper');
    if (!processingWrapper) return;
    
    const interviewId = processingWrapper.dataset.interviewId;
    const stages = document.querySelectorAll('.stage-item');
    
    // Connect to Server-Sent Events (SSE) stream for real-time analysis pipeline progress
    const eventSource = new EventSource(`/process_stream/${interviewId}`);
    
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const currentStage = data.stage; // index 0-8 or "ready"
        const error = data.error;
        
        if (error) {
            alert('Analysis Error: ' + error);
            eventSource.close();
            window.location.href = '/upload';
            return;
        }
        
        if (currentStage === 'ready') {
            eventSource.close();
            // Redirect to results dashboard
            window.location.href = `/results/${interviewId}`;
            return;
        }
        
        // Update stage item classes based on active index
        const stageIndex = parseInt(currentStage);
        
        stages.forEach((stage, idx) => {
            const statusLabel = stage.querySelector('.stage-right');
            const statusDot = stage.querySelector('.stage-status-dot');
            
            if (idx < stageIndex) {
                // Completed stage
                stage.className = 'stage-item completed';
                statusLabel.textContent = 'Completed';
                statusLabel.style.color = 'var(--success)';
            } else if (idx === stageIndex) {
                // Active stage
                stage.className = 'stage-item active';
                statusLabel.textContent = 'Analyzing...';
                statusLabel.style.color = 'var(--primary-blue)';
            } else {
                // Pending stage
                stage.className = 'stage-item pending';
                statusLabel.textContent = 'Pending';
                statusLabel.style.color = 'var(--text-muted)';
            }
        });
    };
    
    eventSource.onerror = function() {
        console.error("SSE connection closed or lost. Falling back to poll check...");
        eventSource.close();
        
        // Fallback polling loop if SSE fails (e.g. proxy constraints)
        const pollInterval = setInterval(() => {
            fetch(`/analyze_status/${interviewId}`)
                .then(res => res.json())
                .then(data => {
                    if (data.stage === 'ready') {
                        clearInterval(pollInterval);
                        window.location.href = `/results/${interviewId}`;
                    } else if (data.error) {
                        clearInterval(pollInterval);
                        alert('Analysis Error: ' + data.error);
                        window.location.href = '/upload';
                    }
                })
                .catch(err => console.error("Polling error:", err));
        }, 1500);
    };
}

// 3. Transcript Search & Highlight Engine
function initTranscriptHighlight() {
    const searchField = document.getElementById('transcript-search-field');
    const transcriptBody = document.getElementById('transcript-body-content');
    
    if (!searchField || !transcriptBody) return;
    
    // Save the original text to restore when clearing search
    const originalHTML = transcriptBody.innerHTML;
    
    searchField.addEventListener('input', () => {
        const query = searchField.value.trim().toLowerCase();
        
        if (!query) {
            transcriptBody.innerHTML = originalHTML;
            highlightFillerWords();
            return;
        }
        
        // Restore to clean copy first
        transcriptBody.innerHTML = originalHTML;
        
        // Apply highlighting to matching terms, ignoring inside tags
        const textNodeIterator = document.createNodeIterator(
            transcriptBody,
            NodeFilter.SHOW_TEXT,
            null
        );
        
        let textNode;
        const nodesToReplace = [];
        
        while (textNode = textNodeIterator.nextNode()) {
            const val = textNode.nodeValue;
            if (val.toLowerCase().includes(query)) {
                nodesToReplace.push(textNode);
            }
        }
        
        nodesToReplace.forEach(node => {
            const val = node.nodeValue;
            const parent = node.parentNode;
            
            // Avoid double-rendering or breaking markup
            if (parent.tagName === 'SPAN' && parent.classList.contains('highlight-fill')) return;
            
            // Create a temp element to hold matching replacements
            const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi');
            const newHTML = val.replace(regex, '<span class="highlight-fill">$1</span>');
            
            const tempSpan = document.createElement('span');
            tempSpan.innerHTML = newHTML;
            
            // Replace old node with new content nodes
            while (tempSpan.firstChild) {
                parent.insertBefore(tempSpan.firstChild, node);
            }
            parent.removeChild(node);
        });
        
        // Re-highlight fillers on top of matches
        highlightFillerWords();
    });
    
    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    // Highlight typical filler words in the transcript automatically
    function highlightFillerWords() {
        const textNodeIterator = document.createNodeIterator(
            transcriptBody,
            NodeFilter.SHOW_TEXT,
            null
        );
        
        const fillerList = ['um', 'uh', 'like', 'actually', 'basically'];
        let textNode;
        const nodesToReplace = [];
        
        while (textNode = textNodeIterator.nextNode()) {
            const val = textNode.nodeValue;
            // Match stand-alone words or surrounded by punctuation
            const hasFiller = fillerList.some(filler => {
                const regex = new RegExp(`\\b${filler}\\b`, 'i');
                return regex.test(val);
            });
            if (hasFiller) {
                nodesToReplace.push(textNode);
            }
        }
        
        nodesToReplace.forEach(node => {
            let val = node.nodeValue;
            const parent = node.parentNode;
            
            if (parent.tagName === 'SPAN' && parent.classList.contains('highlight-filler')) return;
            if (parent.tagName === 'SPAN' && parent.classList.contains('highlight-fill')) return;
            
            let replaced = false;
            fillerList.forEach(filler => {
                const regex = new RegExp(`\\b(${filler})\\b`, 'gi');
                if (regex.test(val)) {
                    val = val.replace(regex, '<span class="highlight-filler">$1</span>');
                    replaced = true;
                }
            });
            
            if (replaced) {
                const tempSpan = document.createElement('span');
                tempSpan.innerHTML = val;
                while (tempSpan.firstChild) {
                    parent.insertBefore(tempSpan.firstChild, node);
                }
                parent.removeChild(node);
            }
        });
    }
    
    // Initial highlight of filler words
    highlightFillerWords();
}

// Helper to draw Dashboard Charts (invoked in results template)
window.initDashboardCharts = function(fillerCounts, speakingSpeed) {
    // 1. Donut Chart for Filler Word Distribution
    const donutCtx = document.getElementById('fillerDonutChart');
    if (donutCtx) {
        new Chart(donutCtx, {
            type: 'doughnut',
            data: {
                labels: ['Um', 'Uh', 'Like', 'Actually', 'Basically'],
                datasets: [{
                    data: [
                        fillerCounts.um || 0,
                        fillerCounts.uh || 0,
                        fillerCounts.like || 0,
                        fillerCounts.actually || 0,
                        fillerCounts.basically || 0
                    ],
                    backgroundColor: [
                        '#3B82F6', // Blue
                        '#60A5FA', // Light Blue
                        '#93C5FD', // Soft Blue
                        '#F59E0B', // Amber
                        '#EF4444'  // Red
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            font: {
                                family: 'Inter',
                                size: 11
                            },
                            boxWidth: 12
                        }
                    }
                },
                cutout: '65%'
            }
        });
    }

    // 2. Half-Donut Gauge Chart for Speaking Speed
    const gaugeCtx = document.getElementById('wpmGaugeChart');
    if (gaugeCtx) {
        // Normal ranges: Slow < 110, Good 110-150, Fast > 150. Max speed mapped is 200.
        const wpmVal = Math.min(200, Math.max(0, speakingSpeed));
        
        new Chart(gaugeCtx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [wpmVal, 200 - wpmVal],
                    backgroundColor: [
                        wpmVal <= 110 ? '#F59E0B' : (wpmVal <= 150 ? '#10B981' : '#EF4444'), // color speed zone
                        '#E5E7EB'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                circumference: 180,
                rotation: 270,
                cutout: '75%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    }
};
