/**
 * script.js
 * Shared SocketIO handler for the ICU state display widgets.
 * Requires elements: #state  #risk  #time
 * Include after socket.io CDN script.
 */

var socket = io();   // connects to the current host automatically

socket.on("update", function(data) {

    var stateEl = document.getElementById("state");
    var riskEl  = document.getElementById("risk");
    var timeEl  = document.getElementById("time");

    if (!stateEl) return;   // page doesn't use this widget

    var state = data.state || data.status || "NORMAL";

    stateEl.innerHTML = state;
    if (riskEl) riskEl.innerHTML = "Risk: " + (data.risk ?? 0) + "%";
    if (timeEl) timeEl.innerHTML = data.time ?? "--";

    // Reset classes then apply the matching one
    stateEl.className = "state-display";
    stateEl.classList.add(state.toLowerCase());
});