// app.js — minimal chat client for the Meridian Wealth Agent API.

(() => {
  const $ = (sel) => document.querySelector(sel);

  const messagesEl  = $("#messages");
  const inputEl     = $("#input");
  const sendBtn     = $("#send");
  const newChatBtn  = $("#new-chat");
  const traceToggle = $("#trace-toggle");
  const statusDot   = $("#status-dot");
  const statusText  = $("#status-text");
  const convIdEl    = $("#conv-id");

  let conversationId = null;
  let inFlight = false;

  // --- Status probe ----------------------------------------------------
  async function checkHealth() {
    try {
      const r = await fetch("/health");
      if (!r.ok) throw new Error(`status ${r.status}`);
      const h = await r.json();
      const ok = h.status === "ok";
      statusDot.className = `dot dot--${ok ? "ok" : "degraded"}`;
      statusText.textContent = ok ? "online" : "degraded";
      statusText.title = `db=${h.db_connected}  vectorstore=${h.vectorstore_loaded}  tavily=${h.tavily_configured}`;
    } catch (err) {
      statusDot.className = "dot dot--error";
      statusText.textContent = "offline";
      statusText.title = String(err);
    }
  }

  // --- Rendering -------------------------------------------------------
  function clearWelcome() {
    const w = messagesEl.querySelector(".welcome");
    if (w) w.remove();
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addMessage(role, text, opts = {}) {
    clearWelcome();
    const wrap = document.createElement("div");
    wrap.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "You" : role === "error" ? "!" : "AI";

    const bubbleWrap = document.createElement("div");
    bubbleWrap.className = "bubble-wrap";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (opts.html) bubble.innerHTML = text;
    else bubble.textContent = text;

    bubbleWrap.appendChild(bubble);

    if (opts.meta) {
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = opts.meta;
      bubbleWrap.appendChild(meta);
    }

    if (opts.toolCalls && opts.toolCalls.length) {
      bubbleWrap.appendChild(renderTrace(opts.toolCalls));
    }

    wrap.appendChild(avatar);
    wrap.appendChild(bubbleWrap);
    messagesEl.appendChild(wrap);
    scrollToBottom();
    return bubble;
  }

  function renderTrace(toolCalls) {
    const details = document.createElement("details");
    details.className = "trace";
    const summary = document.createElement("summary");
    summary.textContent = `Tool calls (${toolCalls.length})`;
    details.appendChild(summary);

    const list = document.createElement("div");
    list.className = "trace-list";
    for (const tc of toolCalls) {
      const card = document.createElement("div");
      card.className = "tool-call";

      const header = document.createElement("div");
      header.className = "tool-call-header";

      const name = document.createElement("span");
      name.className = "tool-name";
      name.textContent = tc.name;
      header.appendChild(name);

      const args = document.createElement("span");
      args.className = "tool-args";
      args.textContent = formatArgs(tc.arguments);
      header.appendChild(args);

      const out = document.createElement("pre");
      out.className = "tool-output";
      out.textContent = tc.output ?? "";

      card.appendChild(header);
      card.appendChild(out);
      list.appendChild(card);
    }
    details.appendChild(list);
    return details;
  }

  function formatArgs(args) {
    if (!args || typeof args !== "object") return "";
    const entries = Object.entries(args);
    if (entries.length === 0) return "()";
    return "(" + entries.map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ") + ")";
  }

  function addTyping() {
    clearWelcome();
    const wrap = document.createElement("div");
    wrap.className = "message assistant typing-msg";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "AI";

    const bubbleWrap = document.createElement("div");
    bubbleWrap.className = "bubble-wrap";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';

    bubbleWrap.appendChild(bubble);
    wrap.appendChild(avatar);
    wrap.appendChild(bubbleWrap);
    messagesEl.appendChild(wrap);
    scrollToBottom();
    return wrap;
  }

  // --- Sending ---------------------------------------------------------
  async function sendMessage(text) {
    if (!text.trim() || inFlight) return;
    inFlight = true;
    sendBtn.disabled = true;

    addMessage("user", text);
    inputEl.value = "";
    autoSize();

    const typing = addTyping();

    const body = {
      message: text,
      include_trace: traceToggle.checked,
      max_iterations: 15,
    };
    if (conversationId) body.conversation_id = conversationId;

    try {
      const r = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      typing.remove();

      if (!r.ok) {
        let detail = `Request failed (HTTP ${r.status})`;
        try {
          const j = await r.json();
          if (j.detail) detail = j.detail;
        } catch (_) { /* not JSON */ }
        addMessage("error", detail);
        return;
      }

      const data = await r.json();
      conversationId = data.conversation_id;
      convIdEl.textContent = `conv: ${conversationId.slice(0, 8)}…`;

      const metaParts = [];
      if (typeof data.iteration_count === "number") metaParts.push(`${data.iteration_count} tool step${data.iteration_count === 1 ? "" : "s"}`);
      if (data.model) metaParts.push(data.model);

      addMessage("assistant", data.answer, {
        meta: metaParts.join(" · "),
        toolCalls: data.tool_calls || [],
      });
    } catch (err) {
      typing.remove();
      addMessage("error", `Network error: ${err.message || err}`);
    } finally {
      inFlight = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  // --- Input UX --------------------------------------------------------
  function autoSize() {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 180) + "px";
  }

  inputEl.addEventListener("input", autoSize);

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputEl.value);
    }
  });

  sendBtn.addEventListener("click", () => sendMessage(inputEl.value));

  newChatBtn.addEventListener("click", () => {
    conversationId = null;
    convIdEl.textContent = "";
    messagesEl.innerHTML = `
      <div class="welcome">
        <h2>New conversation</h2>
        <p>Previous context cleared. Ask anything.</p>
      </div>`;
    inputEl.focus();
  });

  document.querySelectorAll(".suggestion").forEach((btn) => {
    btn.addEventListener("click", () => sendMessage(btn.textContent));
  });

  // --- Boot ------------------------------------------------------------
  checkHealth();
  setInterval(checkHealth, 30000);
  inputEl.focus();
})();
