const state = {
  inputPath: null,
  outputPath: null,
  selectedFiles: new Map(),
  currentJob: null,
  pollTimer: null,
};

const $ = (id) => document.getElementById(id);

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

function humanSize(bytes) {
  if (bytes == null) return "";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes, i = 0;
  while (value >= 1024 && i < units.length - 1) { value /= 1024; i++; }
  return `${value.toFixed(i ? 1 : 0)} ${units[i]}`;
}

function fillRoots(select, roots) {
  select.innerHTML = "";
  for (const root of roots) {
    const option = document.createElement("option");
    option.value = root;
    option.textContent = root;
    select.appendChild(option);
  }
}

async function browseInput(path = null) {
  const query = path ? `&path=${encodeURIComponent(path)}` : "";
  const data = await api(`/api/browse?kind=input${query}`);
  state.inputPath = data.current;
  $("inputPath").textContent = data.current;
  $("inputUp").disabled = !data.parent;
  $("inputUp").dataset.parent = data.parent || "";
  fillRoots($("inputRoot"), data.roots);
  $("inputRoot").value = data.roots.find(r => data.current.startsWith(r)) || data.roots[0];
  renderInputEntries(data.entries);
}

function renderInputEntries(entries) {
  const wrap = $("inputEntries");
  wrap.innerHTML = "";
  if (!entries.length) wrap.innerHTML = '<div class="entry"><span class="meta">此目录没有可显示的视频。</span></div>';
  for (const item of entries) {
    const row = document.createElement("div");
    row.className = "entry";
    const icon = item.type === "directory" ? "📁" : "🎬";
    const selected = state.selectedFiles.has(item.path);
    row.innerHTML = `<span>${icon}</span><span class="name" title="${escapeHtml(item.path)}">${escapeHtml(item.name)}</span><span class="meta">${item.type === "file" ? humanSize(item.size) : ""}</span>`;
    const button = document.createElement("button");
    button.type = "button";
    if (item.type === "directory") {
      button.textContent = "打开";
      button.addEventListener("click", () => browseInput(item.path));
    } else {
      button.textContent = selected ? "已选择" : "选择";
      button.disabled = selected;
      button.addEventListener("click", () => { state.selectedFiles.set(item.path, item.name); renderSelected(); renderInputEntries(entries); preview(); });
    }
    row.appendChild(button);
    wrap.appendChild(row);
  }
}

function renderSelected() {
  $("selectedCount").textContent = state.selectedFiles.size;
  const wrap = $("selectedFiles");
  wrap.innerHTML = "";
  for (const [path, name] of state.selectedFiles) {
    const chip = document.createElement("div");
    chip.className = "chip";
    const text = document.createElement("span"); text.textContent = name; text.title = path;
    const remove = document.createElement("button"); remove.type = "button"; remove.textContent = "×"; remove.title = "移除";
    remove.addEventListener("click", () => { state.selectedFiles.delete(path); renderSelected(); browseInput(state.inputPath); preview(); });
    chip.append(text, remove); wrap.appendChild(chip);
  }
}

async function browseOutput(path = null) {
  const query = path ? `&path=${encodeURIComponent(path)}` : "";
  const data = await api(`/api/browse?kind=output${query}`);
  state.outputPath = data.current;
  $("outputPath").textContent = data.current;
  $("selectedOutput").textContent = data.current;
  $("outputUp").disabled = !data.parent;
  $("outputUp").dataset.parent = data.parent || "";
  fillRoots($("outputRoot"), data.roots);
  $("outputRoot").value = data.roots.find(r => data.current.startsWith(r)) || data.roots[0];
  const wrap = $("outputEntries"); wrap.innerHTML = "";
  const dirs = data.entries.filter(x => x.type === "directory");
  if (!dirs.length) wrap.innerHTML = '<div class="entry"><span class="meta">没有子目录；当前目录可直接作为输出目录。</span></div>';
  for (const item of dirs) {
    const row = document.createElement("div"); row.className = "entry";
    row.innerHTML = `<span>📁</span><span class="name">${escapeHtml(item.name)}</span>`;
    const button = document.createElement("button"); button.type = "button"; button.textContent = "进入"; button.addEventListener("click", () => { browseOutput(item.path); preview(); });
    row.appendChild(button); wrap.appendChild(row);
  }
}

function optionsPayload() {
  const optionalNumber = $("numSamples").value.trim();
  return {
    width: Number($("width").value),
    grid: $("grid").value.trim(),
    num_samples: optionalNumber ? Number(optionalNumber) : null,
    show_timestamp: $("showTimestamp").checked,
    image_format: $("format").value,
    quality: Number($("quality").value),
    start_delay_percent: Number($("startDelay").value),
    end_delay_percent: Number($("endDelay").value),
    timestamp_position: $("timestampPosition").value,
    metadata_position: $("metadataPosition").value,
    background_color: $("backgroundColor").value.trim(),
    metadata_font_color: $("metadataFontColor").value.trim(),
    timestamp_font_color: $("timestampFontColor").value.trim(),
    timestamp_background_color: $("timestampBackgroundColor").value.trim(),
    timestamp_border_color: $("timestampBorderColor").value.trim(),
    accurate: $("accurate").checked,
    fast: $("fast").checked,
    no_overwrite: $("noOverwrite").checked,
    frame_type: $("frameType").value || null,
    interval: $("interval").value.trim() || null,
    manual_timestamps: $("manualTimestamps").value.trim() || null,
    timestamp_format: $("timestampFormat").value,
  };
}

function jobPayload() {
  return { files: [...state.selectedFiles.keys()], output_dir: state.outputPath, options: optionsPayload() };
}

function displayCommand(command) {
  return command.map(arg => /^[A-Za-z0-9_./:{}-]+$/.test(arg) ? arg : JSON.stringify(arg)).join(" \\\n  ");
}

async function preview() {
  if (!state.outputPath || !state.selectedFiles.size) { $("commandPreview").textContent = "请选择视频文件。"; return; }
  try {
    const data = await api("/api/preview", { method: "POST", body: JSON.stringify(jobPayload()) });
    $("commandPreview").textContent = data.commands.map(displayCommand).join("\n\n");
    $("commandPreview").classList.remove("error");
  } catch (err) {
    $("commandPreview").textContent = err.message;
    $("commandPreview").classList.add("error");
  }
}

async function runJob() {
  if (!state.selectedFiles.size) { $("runMessage").textContent = "请先选择至少一个视频。"; return; }
  $("runBtn").disabled = true;
  $("runMessage").textContent = "任务已提交…";
  try {
    const job = await api("/api/jobs", { method: "POST", body: JSON.stringify(jobPayload()) });
    state.currentJob = job.id;
    $("runMessage").textContent = `任务 ${job.id}`;
    startPolling();
  } catch (err) {
    $("runMessage").textContent = err.message;
    $("runMessage").className = "error";
    $("runBtn").disabled = false;
  }
}

function startPolling() {
  clearInterval(state.pollTimer);
  pollJob();
  state.pollTimer = setInterval(pollJob, 1200);
}

async function pollJob() {
  if (!state.currentJob) return;
  try {
    const job = await api(`/api/jobs/${state.currentJob}`);
    $("jobStatus").textContent = `状态：${job.status}${job.current_file ? ` · ${job.current_file}` : ""}`;
    $("jobLog").textContent = job.logs.join("\n");
    $("jobLog").scrollTop = $("jobLog").scrollHeight;
    renderOutputs(job.outputs);
    if (["completed", "failed"].includes(job.status)) {
      clearInterval(state.pollTimer); state.pollTimer = null; $("runBtn").disabled = false;
      $("runMessage").textContent = job.status === "completed" ? "完成" : (job.error || "失败");
      $("runMessage").className = job.status === "failed" ? "error" : "";
    }
  } catch (err) { $("jobStatus").textContent = err.message; }
}

function renderOutputs(outputs) {
  const wrap = $("outputs"); wrap.innerHTML = "";
  for (const path of outputs) {
    const url = `/api/output?path=${encodeURIComponent(path)}`;
    const card = document.createElement("div"); card.className = "output-card";
    const img = document.createElement("img"); img.src = url; img.alt = path;
    const link = document.createElement("a"); link.href = url; link.target = "_blank"; link.rel = "noopener"; link.textContent = path;
    card.append(img, link); wrap.appendChild(card);
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
}

function wireEvents() {
  $("inputUp").addEventListener("click", () => browseInput($("inputUp").dataset.parent));
  $("outputUp").addEventListener("click", () => { browseOutput($("outputUp").dataset.parent); preview(); });
  $("inputRoot").addEventListener("change", e => browseInput(e.target.value));
  $("outputRoot").addEventListener("change", e => { browseOutput(e.target.value); preview(); });
  $("clearFiles").addEventListener("click", () => { state.selectedFiles.clear(); renderSelected(); browseInput(state.inputPath); preview(); });
  $("previewBtn").addEventListener("click", preview);
  $("runBtn").addEventListener("click", runJob);
  document.querySelectorAll("input, select").forEach(el => {
    if (!["inputRoot", "outputRoot"].includes(el.id)) el.addEventListener("change", preview);
  });
}

async function init() {
  wireEvents();
  try {
    await api("/api/health"); $("health").textContent = "● 后端已连接"; $("health").classList.add("ok");
    await Promise.all([browseInput(), browseOutput()]);
  } catch (err) { $("health").textContent = `连接失败：${err.message}`; $("health").classList.add("error"); }
}

init();
