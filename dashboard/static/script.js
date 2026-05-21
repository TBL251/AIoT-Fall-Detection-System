/**
 * script.js
 * Shared Socket.IO handler for AIoT ICU state display widgets.
 *
 * Required DOM elements:  #state  #risk  #time
 * Optional DOM elements:  #fall-alert  #socket-error
 *
 * State → CSS class mapping matches .status-* in style.css:
 *   NORMAL       → status-normal    (green pill)
 *   UNBALANCED   → status-warning   (amber pill)
 *   FALLING      → status-danger    (red pill)
 *   CRITICAL     → status-critical  (red pill, flicker animation)
 *   DISCONNECTED → status-warning   (amber pill, shown on socket loss)
 *
 * Include after the socket.io CDN script tag.
 */

var STATE_CLASS = {
    NORMAL:     "status-normal",
    UNBALANCED: "status-warning",
    FALLING:    "status-danger",
    CRITICAL:   "status-critical",
};

var socket = io();   // connects to the current host automatically

// ── Connection state ──────────────────────────────────────

socket.on("connect", function () {
    _hideSocketError();

    // If the badge was stuck on DISCONNECTED, reset to NORMAL.
    // The server will push the real state on the next update event.
    var stateEl = document.getElementById("state");
    if (stateEl && stateEl.textContent.trim() === "DISCONNECTED") {
        stateEl.textContent = "NORMAL";
        stateEl.className   = "status-badge status-normal";
    }
});

socket.on("connect_error", function () {
    _showSocketError();
    _setDisconnected();
});

socket.on("disconnect", function () {
    _showSocketError();
    _setDisconnected();
});

// ── Data update ───────────────────────────────────────────

socket.on("update", function (data) {
    // Support both #state and #status element IDs for compatibility
    var stateEl = document.getElementById("state") || document.getElementById("status");
    if (!stateEl) return;

    // Prefer data.state; fall back to data.status for legacy payloads
    var state = data.state || data.status || "NORMAL";

    // textContent prevents XSS — never use innerHTML for server data
    stateEl.textContent = state;
    stateEl.className   = "status-badge " + (STATE_CLASS[state] || "status-normal");

    var riskEl = document.getElementById("risk");
    var timeEl = document.getElementById("time");

    if (riskEl) riskEl.textContent = (data.risk ?? 0) + "%";
    if (timeEl) timeEl.textContent = data.time ?? "--:--:--";

    // Optional fall-alert banner
    var alertEl = document.getElementById("fall-alert");
    if (alertEl) {
        alertEl.style.display =
            (state === "FALLING" || state === "CRITICAL") ? "block" : "none";
    }

    // Optional socket-error banner — hide on successful data receipt
    _hideSocketError();
});

// ── Helpers ───────────────────────────────────────────────

function _setDisconnected() {
    var stateEl = document.getElementById("state") || document.getElementById("status");
    if (stateEl) {
        stateEl.textContent = "DISCONNECTED";
        stateEl.className   = "status-badge status-warning";
    }
}

function _showSocketError() {
    var el = document.getElementById("socket-error");
    if (el) el.style.display = "block";
}

function _hideSocketError() {
    var el = document.getElementById("socket-error");
    if (el) el.style.display = "none";
}