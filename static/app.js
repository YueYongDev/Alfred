const state = {
  threads: [],
  activeThreadId: null,
  streaming: false,
  attachments: [],
  agents: [],
  tools: [],
  searchQuery: "",
  // Topology state
  nodes: [], // { id, type, x, y, el, data }
  pan: { x: 0, y: 0 },
  isDraggingNode: false,
};

const els = {
  agentCount: document.getElementById("agent-count"),
  toolCount: document.getElementById("tool-count"),
  messages: document.getElementById("messages-container"),
  input: document.getElementById("user-input"),
  send: document.getElementById("send-btn"),
  threadList: document.getElementById("thread-list"),
  newThreadBtn: document.getElementById("new-thread-btn"),
  threadSearch: document.getElementById("thread-search"),
  tabs: document.getElementById("view-tabs"),
  views: document.querySelectorAll(".view"),
  fileInput: document.getElementById("file-input"),
  attachmentBar: document.getElementById("attachment-bar"),
  // Topology elements
  topologyContainer: document.getElementById("topology-container"),
  topologyNodes: document.getElementById("topology-nodes"),
  networkCanvas: document.getElementById("network-lines"),
  resetViewBtn: document.getElementById("reset-view-btn"),
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

function contentToPlainText(content) {
  if (content === null || content === undefined) return "";
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content.map(contentToPlainText).join(" ");
  }
  if (typeof content === "object") {
    const pieces = [];
    if (typeof content.text === "string") pieces.push(content.text);
    if (typeof content.content === "string") pieces.push(content.content);
    if (typeof content.name === "string") pieces.push(content.name);
    if (typeof content.caption === "string") pieces.push(content.caption);
    // Fallback: try to read nested url/description fields that may carry text
    if (typeof content.url === "string") pieces.push(content.url);
    if (typeof content.description === "string") pieces.push(content.description);
    return pieces.join(" ");
  }
  return "";
}

function renderThreads() {
  els.threadList.innerHTML = "";
  const query = (state.searchQuery || "").trim().toLowerCase();
  let list = !query
    ? state.threads
    : state.threads.filter((thread) => {
        const titleMatch = thread.title.toLowerCase().includes(query);
        const messageMatch = thread.messages.some((msg) => {
          const text = contentToPlainText(msg.content).toLowerCase();
          return text.includes(query);
        });
        return titleMatch || messageMatch;
      });

  const activeThread = getActiveThread();
  if (query && activeThread && !list.includes(activeThread)) {
    list = [activeThread, ...list];
  }

  if (!list.length) {
    const emptyText = query
      ? "没有找到匹配的对话，换个关键词试试。"
      : "暂无历史记录，开始一段新的对话吧。";
    els.threadList.innerHTML = `<div class="loading-item">${emptyText}</div>`;
    return;
  }

  for (const thread of list) {
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
      file: file, // Store the File object
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

function normalizeContentFragments(content) {
  const parts = [];
  if (content === null || content === undefined) return parts;

  if (typeof content === "string") {
    if (content) parts.push({ type: "text", text: content });
    return parts;
  }

  if (Array.isArray(content)) {
    content.forEach((item) => {
      parts.push(...normalizeContentFragments(item));
    });
    return parts;
  }

  if (typeof content === "object") {
    const textVal =
      (content.type === "text" && content.text) ||
      content.text ||
      (typeof content.content === "string" ? content.content : "");
    if (textVal) {
      parts.push({ type: "text", text: textVal });
    }

    const imageUrl =
      (content.image_url && content.image_url.url) ||
      content.image ||
      (content.type === "image_url" ? content.url : "");
    if (imageUrl) {
      parts.push({ type: "image", url: imageUrl });
    }

    const fileValue =
      (content.file && (content.file.url || content.file.path || content.file)) ||
      content.url;
    if (fileValue) {
      parts.push({
        type: "file",
        url: typeof fileValue === "string" ? fileValue : "",
        name: (content.file && content.file.name) || content.name,
      });
    }
  }

  return parts;
}

function contentPartsToMarkdown(parts) {
  const textChunks = [];
  const extras = [];
  for (const part of parts) {
    if (part.type === "text") {
      textChunks.push(part.text);
    } else if (part.type === "image" && part.url) {
      extras.push(`\n\n![image](${part.url})`);
    } else if (part.type === "file" && (part.url || part.name)) {
      const label = part.name || part.url || "file";
      const url = part.url || "#";
      extras.push(`\n\n[${label}](${url})`);
    }
  }
  return `${textChunks.join("")}${extras.join("")}`;
}

function extractContentFromPayload(resp) {
  const messages =
    (resp &&
      resp.payload &&
      resp.payload.output &&
      resp.payload.output.choices &&
      resp.payload.output.choices[0] &&
      resp.payload.output.choices[0].messages) ||
    (resp &&
      resp.output &&
      resp.output.choices &&
      resp.output.choices[0] &&
      resp.output.choices[0].messages) ||
    (resp && resp.choices && resp.choices[0] && resp.choices[0].messages);

  if (!Array.isArray(messages)) return null;

  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const msg = messages[i];
    if (msg && (msg.role === "assistant" || i === messages.length - 1)) {
      return msg.content ?? "";
    }
  }
  return null;
}

// 生成唯一请求ID
function generateReqId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

async function sendMessage() {
  const text = (els.input.value || "").trim();
  const files = [...state.attachments];
  if ((!text && !files.length) || state.streaming) return;

  const thread = getActiveThread();

  // 构建消息内容（支持多模态）
  let userContent = text;

  // 如果有附件，将内容转换为数组格式
  if (files.length > 0) {
    const contentParts = [];

    // 添加文本部分
    if (text) {
      contentParts.push({
        type: "text",
        text: text
      });
    }

    // 处理附件
    for (const att of files) {
      if (att.file) {
        const base64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result);
          reader.onerror = reject;
          reader.readAsDataURL(att.file);
        });

        if (att.type.startsWith("image/")) {
          contentParts.push({
            type: "image_url",
            image_url: {
              url: base64
            }
          });
        } else {
          contentParts.push({
            type: "file",
            file: {
              url: base64,
              name: att.name,
              mime_type: att.type,
              size: att.size
            }
          });
        }
      }
    }

    userContent = contentParts;
  }

  const userMsg = {
    role: "user",
    content: userContent,
    msgId: generateReqId(),
    attachments: files
  };

  thread.messages.push(userMsg);
  thread.updatedAt = Date.now();
  state.messages = thread.messages;

  // 显示用户消息（使用原来的格式用于UI展示）
  const combined = `${text}${attachmentNote(files)}`;
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
    // 构建符合新协议的请求体
    const payload = {
      model: "alfred-router",
      parameters: {
        agentCode: "",
        resultFormat: "message",
        enableSearch: true,
        enableThinking: true
      },
      header: {
        reqId: generateReqId(),
        sessionId: thread.id,
        parentMsgId: "",
        systemParams: {
          userId: "user",
          userIp: "",
          utdId: ""
        }
      },
      body: {
        stream: true,
        messages: thread.messages.map(({ role, content, msgId, meta }) => {
          const msg = { role, content };
          if (msgId) msg.msgId = msgId;
          if (meta) msg.meta = meta;
          return msg;
        })
      }
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
    let assistantContentParts = [];
    
    // 创建一个用于显示工具调用和结果的容器
    const toolCallContainer = document.createElement("div");
    toolCallContainer.className = "tool-call-container";
    assistantContainer.innerHTML = "";
    assistantContainer.appendChild(toolCallContainer);
    
    // 存储工具调用状态
    let currentToolCalls = [];
    let currentFunctionResults = {};

    const handleMessage = (msg) => {
      if (!msg || typeof msg !== "object") return { changed: false };
      let shouldUpdateDisplay = false;

      // 工具调用
      if (msg.role === "assistant" && msg.function_call) {
        const toolCall = {
          id: msg.extra?.function_id || msg.id || "",
          function: {
            name: msg.function_call.name,
            arguments: msg.function_call.arguments || "",
          },
        };
        currentToolCalls.push(toolCall);
        shouldUpdateDisplay = true;
      }
      // 工具返回
      else if (msg.role === "function") {
        const functionId = msg.extra?.function_id || msg.id || msg.tool_call_id || "";
        currentFunctionResults[functionId] = {
          name: msg.name,
          content: msg.content,
        };
        shouldUpdateDisplay = true;
      }

      // 主内容
      if (msg.hasOwnProperty("content")) {
        assistantContentParts.push(...normalizeContentFragments(msg.content));
        assistantText = contentPartsToMarkdown(assistantContentParts);
        shouldUpdateDisplay = true;
      } else {
        const payloadContent = extractContentFromPayload(msg);
        if (payloadContent !== null) {
          assistantContentParts = normalizeContentFragments(payloadContent);
          assistantText = contentPartsToMarkdown(assistantContentParts);
          shouldUpdateDisplay = true;
        }
      }

      return { changed: shouldUpdateDisplay };
    };

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
          let changed = false;

          if (Array.isArray(parsed)) {
            parsed.forEach((msg) => {
              const res = handleMessage(msg);
              if (res.changed) changed = true;
            });
          } else {
            const res = handleMessage(parsed);
            if (res.changed) changed = true;
          }

          if (changed) {
            updateAssistantDisplay(toolCallContainer, currentToolCalls, currentFunctionResults, assistantText);
            scrollToBottom();
          }
        } catch (err) {
          console.warn("Stream parse error", err);
        }
      }
    }
    
    // 处理最终的消息存储
    const finalContent = {
      content: assistantText,
      tool_calls: currentToolCalls,
      function_results: currentFunctionResults,
      raw_content_parts: assistantContentParts
    };
    
    if (assistantText || currentToolCalls.length > 0) {
      thread.messages.push({
        role: "assistant",
        content: assistantText,
        tool_calls: currentToolCalls,
        function_results: currentFunctionResults,
        raw_content_parts: assistantContentParts
      });
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
    requestAnimationFrame(() => {
      // Re-center if first time or needed
      if (state.nodes.length === 0 && state.agents.length > 0) {
        initTopology();
      }
      drawNetworkLines();
    });
  }
}

// --- Topology / Network View Logic ---

function resolveToolsForAgent(agent, tools) {
  const inline = Array.isArray(agent.tools) ? agent.tools : [];
  if (inline.length) return inline;

  // If no inline tools, try to find by name match
  // BUT do not fallback to random tools if none found.
  const byName = tools.filter(
    (t) =>
      t.agent === agent.name ||
      t.agent_name === agent.name ||
      t.owner === agent.name
  );
  return byName;
}

function updateTopologyTransform() {
  const { x, y, k } = state.transform;
  const transform = `translate(${x}px, ${y}px) scale(${k})`;

  // Apply to DOM nodes container
  els.topologyNodes.style.transform = transform;

  // Apply to Background (for parallax or just sync)
  const bg = document.querySelector('.topology-background');
  if (bg) bg.style.transform = transform;

  // Redraw canvas lines
  requestAnimationFrame(drawNetworkLines);
}

function handleZoom(e) {
  e.preventDefault();

  const { x, y, k } = state.transform;
  const zoomFactor = 0.1;
  const direction = e.deltaY > 0 ? -1 : 1;
  let newK = k + direction * zoomFactor;

  // Clamp zoom
  newK = Math.max(0.1, Math.min(newK, 5));

  // Zoom towards mouse pointer
  // worldX = (mouseX - panX) / k
  // newPanX = mouseX - worldX * newK
  const rect = els.topologyContainer.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  const worldX = (mouseX - x) / k;
  const worldY = (mouseY - y) / k;

  const newX = mouseX - worldX * newK;
  const newY = mouseY - worldY * newK;

  state.transform = { x: newX, y: newY, k: newK };
  updateTopologyTransform();
}

function handlePan(e) {
  if (!state.isPanning) return;
  const dx = e.clientX - state.panStart.x;
  const dy = e.clientY - state.panStart.y;

  state.transform.x += dx;
  state.transform.y += dy;
  state.panStart = { x: e.clientX, y: e.clientY };

  updateTopologyTransform();
}

function makeDraggable(el, nodeObj) {
  let startX = 0;
  let startY = 0;
  let initialNodeX = 0;
  let initialNodeY = 0;
  let hasMoved = false;

  const onMouseDown = (e) => {
    // Stop propagation so we don't trigger pan on container
    e.stopPropagation();

    state.isDraggingNode = true;
    hasMoved = false;
    startX = e.clientX;
    startY = e.clientY;
    initialNodeX = nodeObj.x;
    initialNodeY = nodeObj.y;

    // Bring to front
    el.style.zIndex = 100;

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  const onMouseMove = (e) => {
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      hasMoved = true;
    }

    // Adjust dx/dy by zoom level
    const k = state.transform.k;
    nodeObj.x = initialNodeX + dx / k;
    nodeObj.y = initialNodeY + dy / k;

    el.style.transform = `translate(${nodeObj.x}px, ${nodeObj.y}px)`;
    requestAnimationFrame(drawNetworkLines);
  };

  const onMouseUp = () => {
    state.isDraggingNode = false;
    el.style.zIndex = "";
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);

    // If it was a click (not drag), trigger details
    if (!hasMoved) {
      showAgentDetails(nodeObj);
    }
  };

  el.addEventListener("mousedown", onMouseDown);
}

function showAgentDetails(node) {
  const modal = document.getElementById("agent-modal");
  const title = document.getElementById("modal-title");
  const desc = document.getElementById("modal-desc");
  const icon = document.getElementById("modal-icon");
  const list = document.getElementById("modal-tools");

  title.textContent = node.data.name;
  desc.textContent = node.data.description || "暂无描述";

  if (node.type === "router") {
    icon.innerHTML = '<i class="fa-solid fa-server"></i>';
  } else {
    icon.innerHTML = '<i class="fa-solid fa-robot"></i>';
  }

  // Render tools
  const tools = resolveToolsForAgent(node.data, state.tools);
  list.innerHTML = "";

  if (!tools.length) {
    list.innerHTML = '<div style="color:var(--muted); font-size:13px;">该 Agent 暂无公开工具。</div>';
  } else {
    tools.forEach(tool => {
      const item = document.createElement("div");
      item.className = "tool-item";
      const toolName = typeof tool === 'string' ? tool : tool.name;
      const toolDesc = typeof tool === 'string' ? "" : tool.description;

      item.innerHTML = `
        <div class="tool-icon"><i class="fa-solid fa-screwdriver-wrench"></i></div>
        <div class="tool-info">
          <h4>${toolName}</h4>
          <p>${toolDesc || "暂无工具描述"}</p>
        </div>
      `;
      list.appendChild(item);
    });
  }

  modal.classList.add("active");
}

function createNodeElement(node) {
  const el = document.createElement("div");
  el.className = `topology-node ${node.type}`;

  // Initial position
  el.style.transform = `translate(${node.x}px, ${node.y}px)`;

  let icon = '<i class="fa-solid fa-robot"></i>';
  let title = node.data.name;
  let subtitle = node.data.description || "";
  let badges = "";

  if (node.type === "router") {
    icon = '<i class="fa-solid fa-server"></i>';
    subtitle = "智能分发 · 多模态调度";
  } else {
    // Agent
    const tools = resolveToolsForAgent(node.data, state.tools);
    badges = tools
      .slice(0, 3)
      .map((t) => `<span class="tool-badge">${typeof t === 'string' ? t : t.name}</span>`)
      .join("");
    if (tools.length > 3) badges += `<span class="tool-badge">+${tools.length - 3}</span>`;
  }

  el.innerHTML = `
    <div class="node-header">
      <div class="node-icon">${icon}</div>
      <div class="node-info">
        <h3>${title}</h3>
        <p>${subtitle}</p>
      </div>
    </div>
    <div class="node-tools">
      ${badges}
    </div>
  `;

  return el;
}

function initTopology() {
  const { agents, tools } = state;
  els.agentCount.textContent = agents.length;
  els.toolCount.textContent = tools.length;
  els.topologyNodes.innerHTML = "";
  state.nodes = [];

  // Reset transform
  state.transform = { x: 0, y: 0, k: 1 };
  updateTopologyTransform();

  const containerW = els.topologyContainer.clientWidth;
  const containerH = els.topologyContainer.clientHeight;
  const cx = containerW / 2;
  const cy = containerH / 2;

  // 1. Create Router Node (Center)
  const routerNode = {
    id: "router",
    type: "router",
    x: cx - 140, // Center based on width 280
    y: cy - 100,
    data: { name: "Router Agent" },
  };

  // 2. Create Agent Nodes (Circle)
  const radius = 350;
  const agentNodes = agents.map((agent, i) => {
    const angle = (i / agents.length) * 2 * Math.PI - Math.PI / 2; // Start from top
    return {
      id: `agent-${i}`,
      type: "agent",
      x: cx + Math.cos(angle) * radius - 140,
      y: cy + Math.sin(angle) * radius - 60,
      data: agent,
    };
  });

  const allNodes = [routerNode, ...agentNodes];
  state.nodes = allNodes;

  // Render to DOM
  allNodes.forEach((node) => {
    const el = createNodeElement(node);
    node.el = el;
    makeDraggable(el, node);
    els.topologyNodes.appendChild(el);
  });

  drawNetworkLines();
}

function drawNetworkLines() {
  const canvas = els.networkCanvas;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = els.topologyContainer.getBoundingClientRect();

  // Ensure canvas size matches container (screen size)
  if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
  }

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);

  // Apply Pan/Zoom Transform to Context
  const { x, y, k } = state.transform;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);

  const router = state.nodes.find((n) => n.type === "router");
  if (!router) {
    ctx.restore();
    return;
  }

  // Center points of the router node
  const rCx = router.x + 140; // width/2
  const rCy = router.y + 60;  // approx height/2

  state.nodes.forEach((node) => {
    if (node.type === "router") return;

    const nCx = node.x + 140;
    const nCy = node.y + 60;

    // Draw curve
    ctx.beginPath();
    ctx.moveTo(rCx, rCy);

    const cpX = (rCx + nCx) / 2;
    const cpY = (rCy + nCy) / 2;

    ctx.quadraticCurveTo(cpX, cpY, nCx, nCy);

    const gradient = ctx.createLinearGradient(rCx, rCy, nCx, nCy);
    gradient.addColorStop(0, "rgba(59, 130, 246, 0.5)");
    gradient.addColorStop(1, "rgba(139, 92, 246, 0.5)");

    ctx.strokeStyle = gradient;
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.stroke();
  });

  ctx.restore();
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

    // If we are already in network view, init immediately
    if (document.getElementById("network-view").classList.contains("active")) {
      initTopology();
    }
  } catch (err) {
    console.error(err);
  }
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

  if (els.threadSearch) {
    els.threadSearch.addEventListener("input", (e) => {
      state.searchQuery = e.target.value || "";
      renderThreads();
    });
  }

  els.tabs.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab");
    if (!btn) return;
    toggleView(btn.dataset.target);
  });

  els.fileInput.addEventListener("change", handleFileSelect);

  els.resetViewBtn.addEventListener("click", initTopology);

  // Topology Pan/Zoom
  els.topologyContainer.addEventListener("wheel", handleZoom, { passive: false });
  els.topologyContainer.addEventListener("mousedown", (e) => {
    // Only pan if clicking on background (not nodes)
    if (e.target === els.topologyContainer || e.target.classList.contains('topology-background') || e.target === els.networkCanvas) {
      state.isPanning = true;
      state.panStart = { x: e.clientX, y: e.clientY };
      els.topologyContainer.style.cursor = "grabbing";
    }
  });

  window.addEventListener("mousemove", (e) => {
    if (state.isPanning) handlePan(e);
  });

  window.addEventListener("mouseup", () => {
    state.isPanning = false;
    els.topologyContainer.style.cursor = "grab";
  });

  window.addEventListener("resize", () => {
    requestAnimationFrame(drawNetworkLines);
  });

  // Modal Close
  document.getElementById("modal-close").addEventListener("click", () => {
    document.getElementById("agent-modal").classList.remove("active");
  });
  document.getElementById("agent-modal").addEventListener("click", (e) => {
    if (e.target.id === "agent-modal") {
      e.target.classList.remove("active");
    }
  });
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

function createToolCallElement(toolCall, result) {
  const toolElement = document.createElement("div");
  toolElement.className = "tool-call-block";
  
  const functionName = toolCall.function.name;
  const argumentsStr = toolCall.function.arguments;
  let argsPretty = argumentsStr;
  
  try {
    // 尝试格式化 JSON 参数
    const argsObj = JSON.parse(argumentsStr);
    argsPretty = JSON.stringify(argsObj, null, 2);
  } catch (e) {
    // 如果不是有效JSON，保持原样
  }
  
  toolElement.innerHTML = `
    <div class="tool-header">
      <div class="tool-icon"><i class="fa-solid fa-bolt"></i></div>
      <div class="tool-info">
        <div class="tool-name">${functionName}</div>
        <details class="tool-args">
          <summary>参数</summary>
          <pre class="tool-args-content">${argsPretty}</pre>
        </details>
      </div>
    </div>
    ${result ? `
    <div class="tool-result-container">
      <div class="tool-result-header">
        <span class="tool-result-label">执行结果</span>
        <button class="toggle-result-btn" data-collapsed="false">收起</button>
      </div>
      <div class="tool-result-content">
        <pre class="tool-result-data">${result}</pre>
      </div>
    </div>
    ` : ''}
  `;
  
  // 添加切换结果显示的事件监听
  const toggleBtn = toolElement.querySelector('.toggle-result-btn');
  if (toggleBtn) {
    const resultContent = toolElement.querySelector('.tool-result-content');
    toggleBtn.addEventListener('click', () => {
      const isCollapsed = toggleBtn.dataset.collapsed === 'true';
      if (isCollapsed) {
        resultContent.style.display = 'block';
        toggleBtn.textContent = '收起';
        toggleBtn.dataset.collapsed = 'false';
      } else {
        resultContent.style.display = 'none';
        toggleBtn.textContent = '展开';
        toggleBtn.dataset.collapsed = 'true';
      }
    });
  }
  
  return toolElement;
}

function updateAssistantDisplay(container, toolCalls, functionResults, mainContent) {
  container.innerHTML = '';
  
  // 显示工具调用及其结果
  toolCalls.forEach((toolCall, index) => {
    const functionId = toolCall.id;
    const result = functionResults[functionId] ? functionResults[functionId].content : null;
    const toolElement = createToolCallElement(toolCall, result);
    container.appendChild(toolElement);
  });
  
  // 如果有主内容，创建内容块
  if (mainContent) {
    const contentElement = document.createElement("div");
    contentElement.className = "main-content-block";
    contentElement.innerHTML = htmlFromMarkdown(mainContent);
    container.appendChild(contentElement);
  }
}
