// Small progressive enhancement for the Work IQ emulator viewer. No frameworks.
// Thread view: polls the thread every 4 seconds. Board: polls the run status and reloads when it changes.
(function () {
  "use strict";
  var POLL_MS = 4000;

  function getJson(url) {
    return fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" }, cache: "no-store" }).then(function (r) {
      if (!r.ok) { throw new Error("HTTP " + r.status); }
      return r.json();
    });
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) { e.className = cls; }
    if (text !== undefined) { e.textContent = text; }
    return e;
  }

  var thread = document.getElementById("thread");
  if (thread) {
    var src = thread.getAttribute("data-src");
    var status = document.getElementById("thread-status");
    var autoState = document.getElementById("auto-sam-state");
    var lastKey = "";
    var render = function (data) {
      var key = data.messages.map(function (m) { return m.id; }).join(",");
      if (key !== lastKey) {
        var nearBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 80;
        while (thread.firstChild) { thread.removeChild(thread.firstChild); }
        data.messages.forEach(function (m) {
          var li = el("li", m.agent ? "msg agent" : "msg");
          var meta = el("div", "meta");
          meta.appendChild(el("strong", "", m.from));
          meta.appendChild(document.createTextNode(" "));
          meta.appendChild(el("span", "muted", m.time));
          li.appendChild(meta);
          li.appendChild(el("div", "body", m.text));
          thread.appendChild(li);
        });
        if (lastKey && nearBottom) { thread.lastChild.scrollIntoView({ block: "nearest" }); }
        lastKey = key;
      }
      if (autoState) { autoState.textContent = data.autoSam ? "on" : "off"; }
      var storyTime = document.getElementById("story-time");
      if (storyTime && data.storyTime) { storyTime.textContent = data.storyTime; }
      status.textContent = (data.samTyping ? "Sam is typing. " : "") + "Updated " + new Date().toLocaleTimeString() + ". This thread refreshes every 4 seconds.";
    };
    var poll = function () {
      getJson(src).then(render).catch(function (err) { status.textContent = "Could not refresh the thread (" + err.message + "). Retrying."; });
    };
    setInterval(poll, POLL_MS);
    poll();
  }

  var boardStatus = document.getElementById("board-status");
  if (boardStatus) {
    var runId = boardStatus.getAttribute("data-run");
    var runStatus = boardStatus.getAttribute("data-status");
    var form = document.getElementById("run-form");
    var button = document.getElementById("run-button");
    var started = null;
    var check = function () {
      getJson("/viewer/api/board").then(function (data) {
        if ((data.id || "") !== runId || data.status !== runStatus) {
          if (data.status === "running" && runStatus !== "running") {
            runId = data.id; runStatus = data.status; started = data.started * 1000;
            button.disabled = true;
          } else {
            window.location.reload();
            return;
          }
        }
        if (data.status === "running") {
          started = started || data.started * 1000;
          var secs = Math.max(0, Math.round((Date.now() - started) / 1000));
          boardStatus.textContent = "Running: Maria's agent is asking the suppliers (" + secs + " s). This takes 30 to 90 seconds.";
        }
      }).catch(function () { /* keep the last state on screen */ });
    };
    if (form && button) {
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        button.disabled = true;
        boardStatus.textContent = "Starting the run.";
        fetch(form.action, { method: "POST", credentials: "same-origin", headers: { Accept: "application/json" } })
          .then(function () { window.location.reload(); })
          .catch(function () { window.location.reload(); });
        setTimeout(check, 1000);
      });
    }
    setInterval(check, POLL_MS);
  }
})();
