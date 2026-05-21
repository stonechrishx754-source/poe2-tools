/**
 * POE2 Analytics — Client-side JavaScript
 *
 * Handles: SSE connection, clipboard copy, Chart.js helpers.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Request notification permission for deal alerts
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
});

/**
 * Copy text to clipboard. Used by the "Copy Whisper" button on deal alerts.
 */
function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Copied to clipboard');
        }).catch(() => {
            fallbackCopy(text);
        });
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('Copied to clipboard');
}

function showToast(msg) {
    const toast = document.createElement('div');
    toast.className = 'position-fixed bottom-0 end-0 m-3 p-3 bg-dark text-light border border-info rounded';
    toast.style.zIndex = '9999';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
}

/**
 * HTMX event handlers
 */
document.addEventListener('htmx:afterSwap', (e) => {
    // Re-initialize any Chart.js canvases after HTMX swaps
    if (e.target.querySelector('canvas')) {
        // Charts are initialized by inline scripts in the fragments
    }
});

document.addEventListener('htmx:responseError', (e) => {
    console.error('HTMX request failed:', e.detail.xhr.status, e.detail.xhr.statusText);
});
