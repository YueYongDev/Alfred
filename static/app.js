const state = {
  threads: [],
  activeThreadId: null,
  streaming: false,
  attachments: [],
  agents: [],
  tools: [],
};

const els = {
  agentCount: document.getElementById("agent-count"),
  toolCount: document.getElementById("tool-count"),
  messages: document.getElementById("messages-container"),
  input: document.getElementById("user-input"),
  send: document.getElementById("send-btn"),
  threadList: document.getElementById("thread-list"),
  newThreadBtn: document.getElementById("new-thread-btn"),
  tabs: document.getElementById("view-tabs"),
  views: document.querySelectorAll(".view"),
  fileInput: document.getElementById("file-input"),
  attachmentBar: document.getElementById("attachment-bar"),
  agentGrid: document.getElementById("agent-grid"),
  networkCanvas: document.getElementById("network-lines"),
};

const decoder = new TextDecoder();

function htmlFromMarkdown(text) {
  if (!text) return "";
  return marked.parse(text, { breaks: true });
}

function scrollToBottom() {
  els.messages.scrollTop = els.messages.scrollHeight;
}

function getActiveThread() {
  return state.threads.find((t) => t.id === state.activeThreadId);
}

function formatTime(ts) {
  const date = ts ? new Date(ts) : new Date();
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function renderThreads() {
  els.threadList.innerHTML = "";
  if (!state.threads.length) {
    els.threadList.innerHTML =
      '<div class="loading-item">暂无历史记录，开始一段新的对话吧。</div>';
    return;
  }

  for (const thread of state.threads) {
    const div = document.createElement("div");
    div.className = `thread ${thread.id === state.activeThreadId ? "active" : ""}`;
    div.dataset.id = thread.id;
    div.innerHTML = `
      <div class="thread-title">${thread.title}</div>
      <div class="thread-meta">
        <span><i class="fa-regular fa-clock"></i> ${formatTime(thread.updatedAt)}</span>
        <span>${thread.messages.length} 条</span>
      </div>
    `;
    div.addEventListener("click", () => setActiveThread(thread.id));
    els.threadList.appendChild(div);
  }
}

function renderAttachmentsPreview(list, container) {
  if (!list?.length) return;
  const wrap = document.createElement("div");
  wrap.className = "attachments";
  for (const item of list) {
    const chip = document.createElement("div");
    chip.className = "attachment-chip";
    if (item.preview) {
      const img = document.createElement("img");
      img.src = item.preview;
      img.alt = item.name;
      chip.appendChild(img);
    } else {
      chip.innerHTML = '<i class="fa-regular fa-file"></i>';
    }
    const name = document.createElement("span");
    name.textContent = item.name;
    chip.appendChild(name);
    wrap.appendChild(chip);
  }
  container.appendChild(wrap);
}

function appendMessage(role, content, attachments = []) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  const inner = document.createElement("div");
  inner.className = "message-content";
  inner.innerHTML = htmlFromMarkdown(content);
  wrapper.appendChild(inner);
  if (attachments.length) {
    renderAttachmentsPreview(attachments, wrapper);
  }
  els.messages.appendChild(wrapper);
  scrollToBottom();
  return inner;
}

function renderMessages(thread) {
  els.messages.innerHTML = "";
  if (!thread || !thread.messages.length) {
    appendMessage("system", "新的对话已就绪，告诉我你的需求吧。");
    return;
  }
  for (const msg of thread.messages) {
    appendMessage(msg.role, msg.content, msg.attachments || []);
  }
}

function setActiveThread(id) {
  state.activeThreadId = id;
  const thread = getActiveThread();
  state.messages = thread ? thread.messages : [];
  renderThreads();
  renderMessages(thread);
}

function createThread(title = "全新对话") {
  const newThread = {
    id: `t-${Date.now()}`,
    title,
    updatedAt: Date.now(),
    messages: [
      {
        role: "system",
        content:
          "你好，我是 Alfred Router Agent，可以为你调度子 Agent 与工具完成任务。",
      },
    ],
  };
  state.threads.unshift(newThread);
  return newThread.id;
}

function updateAttachmentBar() {
  els.attachmentBar.innerHTML = "";
  for (const [index, file] of state.attachments.entries()) {
    const pill = document.createElement("div");
    pill.className = "attachment-pill";
    pill.innerHTML = `<i class="fa-regular fa-file-lines"></i> ${file.name}`;
    const remove = document.createElement("button");
    remove.innerHTML = '<i class="fa-solid fa-xmark"></i>';
    remove.addEventListener("click", () => {
      state.attachments.splice(index, 1);
      updateAttachmentBar();
    });
    pill.appendChild(remove);
    els.attachmentBar.appendChild(pill);
  }
}

function handleFileSelect(event) {
  const files = Array.from(event.target.files || []);
  const mapped = files.map((file) => {
    const isImage = file.type.startsWith("image/");
    const preview = isImage ? URL.createObjectURL(file) : "";
    return {
      name: file.name,
      type: file.type,
      size: file.size,
      preview,
    };
  });
  state.attachments.push(...mapped);
  updateAttachmentBar();
}

function attachmentNote(attachments) {
  if (!attachments.length) return "";
  const lines = attachments.map(
    (a, i) => `${i + 1}. ${a.name} (${a.type || "file"})`
  );
  return `\n\n[附件]\n${lines.join("\n")}`;
}

function setSending(isSending) {
  state.streaming = isSending;
  els.send.disabled = isSending;
  els.input.disabled = isSending;
  els.fileInput.disabled = isSending;
  els.send.innerHTML = isSending
    ? '<i class="fa-solid fa-spinner fa-spin"></i>'
    : '<i class="fa-solid fa-paper-plane"></i>';
}

async function sendMessage() {
  const text = (els.input.value || "").trim();
  const files = [...state.attachments];
  if ((!text && !files.length) || state.streaming) return;

  const combined = `${text}${attachmentNote(files)}`;
  const userMsg = { role: "user", content: combined, attachments: files };
  const thread = getActiveThread();
  thread.messages.push(userMsg);
  thread.updatedAt = Date.now();
  state.messages = thread.messages;

  appendMessage("user", combined, files);
  els.input.value = "";
  state.attachments = [];
  els.fileInput.value = "";
  updateAttachmentBar();
  autoResize();

  const assistantContainer = appendMessage(
    "assistant",
    "_Alfred 正在思考与调度..._"
  );

  setSending(true);
  try {
    const payload = {
      model: "alfred-router",
      stream: true,
      messages: thread.messages.map(({ role, content }) => ({ role, content })),
    };
    const res = await fetch("/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok || !res.body) {
      throw new Error(`HTTP ${res.status}`);
    }

    let buffer = "";
    let assistantText = "";
    const reader = res.body.getReader();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const data = line.replace(/^data:\s*/, "");
        if (data === "[DONE]") {
          buffer = "";
          break;
        }
        try {
          const parsed = JSON.parse(data);
          const delta = parsed?.choices?.[0]?.delta?.content || "";
          if (!delta) continue;
          assistantText += delta;
          assistantContainer.innerHTML = htmlFromMarkdown(assistantText);
          scrollToBottom();
        } catch (err) {
          console.warn("Stream parse error", err);
        }
      }
    }

    if (assistantText) {
      thread.messages.push({ role: "assistant", content: assistantText });
      thread.updatedAt = Date.now();
      state.messages = thread.messages;
    } else {
      assistantContainer.innerHTML = "No response received.";
    }
  } catch (err) {
    console.error(err);
    assistantContainer.innerHTML =
      "Request failed. Please check the server logs.";
  } finally {
    renderThreads();
    setSending(false);
  }
}

function autoResize() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(els.input.scrollHeight, 180)}px`;
}

function toggleView(targetId) {
  els.views.forEach((view) => {
    view.classList.toggle("active", view.id === targetId);
  });
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.target === targetId);
  });

  if (targetId === "network-view") {
    requestAnimationFrame(drawNetworkLines);
  }
}

function resolveToolsForAgent(agent, tools) {
  const inline = Array.isArray(agent.tools) ? agent.tools : [];
  if (inline.length) return inline;

  const byName = tools.filter(
    (t) =>
      t.agent === agent.name ||
      t.agent_name === agent.name ||
      t.owner === agent.name
  );
  if (byName.length) return byName;
  return tools.slice(0, 4);
}

function renderNetwork() {
  const { agents, tools } = state;
  els.agentCount.textContent = agents.length;
  els.toolCount.textContent = tools.length;

  if (!agents.length && !tools.length) {
    els.agentGrid.innerHTML =
      '<div class="loading-item">暂无 Agent/Tool，检查服务端配置。</div>';
    return;
  }

  els.agentGrid.innerHTML = "";
  agents.forEach((agent) => {
    const toolsForAgent = resolveToolsForAgent(agent, tools).map((t) =>
      typeof t === "string" ? { name: t } : t
    );

    const toolBadges = toolsForAgent
      .slice(0, 4)
      .map((t) => `<span class="mini tool">${t.name}</span>`)
      .join("");

    const card = document.createElement("div");
    card.className = "agent-card";

    card.innerHTML = `
      <div class="agent-head">
        <div class="agent-icon"><i class="fa-solid fa-hexagon-nodes"></i></div>
        <div>
          <div class="agent-name">${agent.name}</div>
          <div class="agent-desc">${agent.description || "智能 Agent"}</div>
        </div>
      </div>
      <div class="badge-row">
        <span class="mini status"><span class="dot online"></span> 在线</span>
        <span class="mini">Router 路由</span>
        ${toolBadges}
      </div>
    `;
    els.agentGrid.appendChild(card);
  });
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status}`);
  return res.json();
}

async function loadMetadata() {
  try {
    const [agents, tools] = await Promise.all([
      fetchJson("/api/agents"),
      fetchJson("/api/tools"),
    ]);
    state.agents = agents;
    state.tools = tools;
    renderNetwork();
  } catch (err) {
    console.error(err);
    els.agentGrid.innerHTML =
      '<div class="loading-item error">Agent/Tool 加载失败</div>';
  }
}

function drawNetworkLines() {
  const canvas = els.networkCanvas;
  const container = canvas?.parentElement;
  if (!canvas || !container) return;

  const ctx = canvas.getContext("2d");
  const cards = container.querySelectorAll(".agent-card");
  const router = container.querySelector(".router-icon");
  if (!ctx || !router) return;

  const dpr = window.devicePixelRatio || 1;
  const width = container.clientWidth;
  const height = container.clientHeight;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const containerRect = container.getBoundingClientRect();
  const routerRect = router.getBoundingClientRect();
  const start = {
    x: routerRect.left - containerRect.left + routerRect.width / 2,
    y: routerRect.top - containerRect.top + routerRect.height,
  };

  cards.forEach((card) => {
    const rect = card.getBoundingClientRect();
    const end = {
      x: rect.left - containerRect.left + rect.width / 2,
      y: rect.top - containerRect.top,
    };
    const midY = (start.y + end.y) / 2 - 12;
    const gradient = ctx.createLinearGradient(start.x, start.y, end.x, end.y);
    gradient.addColorStop(0, "rgba(45, 107, 231, 0.42)");
    gradient.addColorStop(1, "rgba(17, 210, 238, 0.6)");

    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.quadraticCurveTo((start.x + end.x) / 2, midY, end.x, end.y + 6);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.shadowColor = "rgba(45, 107, 231, 0.15)";
    ctx.shadowBlur = 8;
    ctx.stroke();
  });
}

function bindEvents() {
  els.send.addEventListener("click", sendMessage);
  els.input.addEventListener("input", autoResize);
  els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  els.newThreadBtn.addEventListener("click", () => {
    const id = createThread("新的路由对话");
    renderThreads();
    setActiveThread(id);
  });

  els.tabs.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab");
    if (!btn) return;
    toggleView(btn.dataset.target);
  });

  els.fileInput.addEventListener("change", handleFileSelect);

  if (els.agentGrid) {
    els.agentGrid.addEventListener(
      "scroll",
      () => requestAnimationFrame(drawNetworkLines),
      { passive: true }
    );
  }
  window.addEventListener("resize", () => requestAnimationFrame(drawNetworkLines));
}

function initThreads() {
  if (state.threads.length) return;
  const id = createThread("多 Agent 调度演示");
  setActiveThread(id);
}

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  autoResize();
  initThreads();
  renderThreads();
  renderMessages(getActiveThread());
  loadMetadata();
});
