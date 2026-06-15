/**
 * OpenClaw Web Playground Client Logic
 * Implements real-time WebSocket protocol interaction.
 */

let socket = null;
let currentAgentMessageElement = null;
let currentThinkingElement = null;
let currentAgentText = "";
let reqIdCounter = 1;

// DOM Cache
const hostInput = document.getElementById("host");
const portInput = document.getElementById("port");
const tokenInput = document.getElementById("token");
const sessionKeyInput = document.getElementById("session-key");
const connectBtn = document.getElementById("connect-btn");
const connectStatus = document.getElementById("connection-status");
const statusIndicator = connectStatus.querySelector(".status-indicator");
const statusText = connectStatus.querySelector(".status-text");

const connIdVal = document.getElementById("conn-id");
const serverVersionVal = document.getElementById("server-version");
const protocolVerVal = document.getElementById("protocol-ver");

const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");

const logEntries = document.getElementById("log-entries");
const clearLoggerBtn = document.getElementById("clear-logger-btn");

// Logger Utilities
function logFrame(direction, data) {
  // Remove placeholder if present
  const placeholder = logEntries.querySelector(".log-placeholder");
  if (placeholder) {
    placeholder.remove();
  }

  const entry = document.createElement("div");
  entry.classList.add("log-entry");
  entry.classList.add(direction);

  // Check if it is a heartbeat (tick) to keep logs cleaner
  const isHeartbeat = data?.type === "event" && data?.event === "tick";
  if (isHeartbeat) {
    entry.classList.add("heartbeat");
  }

  const timeSpan = document.createElement("span");
  timeSpan.classList.add("log-time");
  const now = new Date();
  timeSpan.textContent = `${now.toLocaleTimeString()}.${String(now.getMilliseconds()).padStart(3, "0")} | ${direction === "out" ? "SENT (req)" : "RECV (" + (data.type || "frame") + ")"}`;
  
  entry.appendChild(timeSpan);

  const code = document.createElement("code");
  code.textContent = JSON.stringify(data, null, 2);
  entry.appendChild(code);

  logEntries.appendChild(entry);
  logEntries.scrollTop = logEntries.scrollHeight;
}

// Clear Logger
clearLoggerBtn.addEventListener("click", () => {
  logEntries.innerHTML = '<div class="log-placeholder">Clear log history. Standing by for frames...</div>';
});

// Update UI Connection State
function setStatus(state) {
  statusIndicator.className = "status-indicator";
  if (state === "connected") {
    statusIndicator.classList.add("connected");
    statusText.textContent = "Connected";
    connectBtn.textContent = "Disconnect Gateway";
    connectBtn.className = "btn btn-secondary";
    chatInput.disabled = false;
    sendBtn.disabled = false;
  } else if (state === "connecting") {
    statusIndicator.classList.add("connecting");
    statusText.textContent = "Connecting...";
    connectBtn.textContent = "Connecting...";
    connectBtn.disabled = true;
    chatInput.disabled = true;
    sendBtn.disabled = true;
  } else {
    statusIndicator.classList.add("disconnected");
    statusText.textContent = "Disconnected";
    connectBtn.textContent = "Connect Gateway";
    connectBtn.className = "btn btn-primary";
    connectBtn.disabled = false;
    chatInput.disabled = true;
    sendBtn.disabled = true;
    
    // Clear Session Info
    connIdVal.textContent = "-";
    serverVersionVal.textContent = "-";
    protocolVerVal.textContent = "-";
  }
}

// Handle Connection Lifecycle
function connect() {
  const host = hostInput.value.trim() || "127.0.0.1";
  const port = portInput.value.trim() || "18789";
  const token = tokenInput.value.trim();

  setStatus("connecting");

  // OpenClaw allows authentication using standard WS URL tokens as fallback,
  // or via headers, but browser WS APIs do not support custom headers.
  // We can pass token as query parameter: `?token=<token>` or `?authorization=Bearer <token>`
  const queryParam = token ? `?token=${encodeURIComponent(token)}` : "";
  const url = `ws://${host}:${port}/${queryParam}`;

  try {
    socket = new WebSocket(url);
  } catch (err) {
    addSystemMessage(`Connection error: ${err.message}`);
    setStatus("disconnected");
    return;
  }

  socket.onopen = () => {
    addSystemMessage("WebSocket channel opened. Initiating OpenClaw handshake protocol...");
    
    // Send connect handshake frame
    const handshakeReqId = `handshake-${reqIdCounter++}`;
    const handshakeFrame = {
      type: "req",
      id: handshakeReqId,
      method: "connect",
      params: {
        minProtocol: 1,
        maxProtocol: 1,
        client: {
          id: "openclaw-web-playground",
          displayName: "Web Playground Client",
          version: "1.0.0",
          platform: "Browser",
          mode: "operator"
        }
      }
    };
    
    socket.send(JSON.stringify(handshakeFrame));
    logFrame("out", handshakeFrame);
  };

  socket.onmessage = (event) => {
    try {
      const frame = JSON.parse(event.data);
      logFrame("in", frame);

      // Handle Handshake Response
      if (frame.type === "res" && frame.id.startsWith("handshake-")) {
        if (frame.ok) {
          const hello = frame.payload;
          connIdVal.textContent = hello.server?.connId || "N/A";
          serverVersionVal.textContent = hello.server?.version || "N/A";
          protocolVerVal.textContent = `v${hello.protocol}`;
          setStatus("connected");
          addSystemMessage("Handshake completed! Authentication successful. OpenClaw Gateway ready.");
        } else {
          addSystemMessage(`Handshake rejected: ${frame.error?.message || "Unauthorized"}`);
          socket.close();
        }
        return;
      }

      // Handle RPC method responses
      if (frame.type === "res") {
        if (!frame.ok) {
          addSystemMessage(`Request failed: ${frame.error?.message || "Unknown error"}`);
          finalizeStreaming();
        }
        return;
      }

      // Handle Gateway Push Events
      if (frame.type === "event") {
        const eventName = frame.event;
        const payload = frame.payload || {};

        if (eventName === "chat.event") {
          const state = payload.state;
          if (state === "delta") {
            handleStreamingDelta(payload);
          } else if (state === "final") {
            finalizeStreaming();
          } else if (state === "aborted" || state === "error") {
            finalizeStreaming(payload.errorMessage || payload.stopReason || "Aborted");
          }
        }
      }
    } catch (err) {
      console.error("Error parsing WebSocket frame: ", err);
    }
  };

  socket.onclose = (event) => {
    addSystemMessage(`Connection closed. Code: ${event.code} ${event.reason ? "(" + event.reason + ")" : ""}`);
    setStatus("disconnected");
    socket = null;
    finalizeStreaming();
  };

  socket.onerror = (err) => {
    addSystemMessage("WebSocket encountered an error.");
    console.error("WS error: ", err);
  };
}

function disconnect() {
  if (socket) {
    socket.close();
  }
}

// Chat UI management
function addSystemMessage(text) {
  const msg = document.createElement("div");
  msg.classList.add("system-message");
  msg.textContent = text;
  chatMessages.appendChild(msg);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addUserMessage(text) {
  const msg = document.createElement("div");
  msg.classList.add("user-message");
  msg.textContent = text;
  chatMessages.appendChild(msg);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function handleStreamingDelta(payload) {
  // Create message bubble if it doesn't exist yet
  if (!currentAgentMessageElement) {
    currentAgentMessageElement = document.createElement("div");
    currentAgentMessageElement.classList.add("agent-message");
    chatMessages.appendChild(currentAgentMessageElement);
  }

  // Handle agent reasoning thoughts
  const deltaText = payload.deltaText || "";
  const reasoning = payload.message?.reasoning || payload.usage?.reasoning;
  
  if (reasoning) {
    if (!currentThinkingElement) {
      currentThinkingElement = document.createElement("div");
      currentThinkingElement.classList.add("thinking-block");
      currentThinkingElement.textContent = "Thinking... ";
      currentAgentMessageElement.appendChild(currentThinkingElement);
    }
    currentThinkingElement.textContent += deltaText;
  } else {
    // Normal agent reply text
    currentAgentText += deltaText;
    
    // Simple markdown newline preservation
    const formattedText = currentAgentText.replace(/\n/g, "<br>");
    
    // Exclude the thinking block when updating main innerHTML
    if (currentThinkingElement) {
      // Keep thinking block at the top, update the text after it
      let textContainer = currentAgentMessageElement.querySelector(".reply-text");
      if (!textContainer) {
        textContainer = document.createElement("span");
        textContainer.classList.add("reply-text");
        currentAgentMessageElement.appendChild(textContainer);
      }
      textContainer.innerHTML = formattedText;
    } else {
      currentAgentMessageElement.innerHTML = formattedText;
    }
  }

  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function finalizeStreaming(errorText = "") {
  if (errorText) {
    if (currentAgentMessageElement) {
      currentAgentMessageElement.innerHTML += `<br><span style="color: var(--status-disconnected); font-style: italic;">(${errorText})</span>`;
    } else {
      addSystemMessage(`Stream error: ${errorText}`);
    }
  }
  
  currentAgentMessageElement = null;
  currentThinkingElement = null;
  currentAgentText = "";
}

// Send Chat Message
function sendChat() {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    addSystemMessage("Not connected to gateway.");
    return;
  }

  const text = chatInput.value.trim();
  if (!text) return;

  addUserMessage(text);
  chatInput.value = "";

  const sendReqId = `chatsend-${reqIdCounter++}`;
  const sessionKey = sessionKeyInput.value.trim() || "global";
  const idempotencyKey = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2);

  const requestFrame = {
    type: "req",
    id: sendReqId,
    method: "chat.send",
    params: {
      sessionKey: sessionKey,
      message: text,
      idempotencyKey: idempotencyKey
    }
  };

  socket.send(JSON.stringify(requestFrame));
  logFrame("out", requestFrame);
}

// Event Listeners
connectBtn.addEventListener("click", () => {
  if (socket) {
    disconnect();
  } else {
    connect();
  }
});

sendBtn.addEventListener("click", sendChat);

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendChat();
  }
});
