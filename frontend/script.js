// frontend/script.js (FULL)
const tasksLocal = [];

document.getElementById("add-task").addEventListener("click", () => {
  const title = document.getElementById("title").value.trim();
  if (!title) { alert("Title required"); return; }
  const due_date = document.getElementById("due_date").value || null;
  const estimated_hours = parseFloat(document.getElementById("estimated_hours").value) || 1;
  const importance = parseInt(document.getElementById("importance").value) || 5;
  const depsRaw = document.getElementById("dependencies").value.trim();
  const dependencies = depsRaw ? depsRaw.split(",").map(s => s.trim()).filter(Boolean) : [];

  const id = title.toLowerCase().replace(/\s+/g, "_") + "_" + (tasksLocal.length+1);
  tasksLocal.push({ id, title, due_date, estimated_hours, importance, dependencies });
  document.getElementById("title").value = "";
  document.getElementById("due_date").value = "";
  document.getElementById("dependencies").value = "";
  renderLocalTasks();
});

function renderLocalTasks() {
  const results = document.getElementById("results");
  const list = tasksLocal.map(t =>
    `<div class="task-card"><strong>${t.title}</strong>
    <div class="small">id: ${t.id} | due: ${t.due_date||'—'} |
    hours: ${t.estimated_hours} | importance: ${t.importance}</div></div>`
  ).join("");
  results.innerHTML = `<h3>Local tasks (${tasksLocal.length})</h3>${list}`;
}

document.getElementById("analyze").addEventListener("click", async () => {
  const jsonText = document.getElementById("json-input").value.trim();
  let payload = [];
  if (jsonText) {
    try {
      payload = JSON.parse(jsonText);
      if (!Array.isArray(payload)) { alert("JSON must be an array of tasks"); return; }
    } catch (e) { alert("Invalid JSON"); return; }
  } else {
    if (tasksLocal.length === 0) { alert("Add tasks or paste JSON"); return; }
    payload = tasksLocal;
  }

  const strategy = document.getElementById("strategy").value;
  const loadingEl = document.getElementById("loading");
  loadingEl.style.display = "block";
  try {
    const resp = await fetch("http://127.0.0.1:8000/api/tasks/analyze/?strategy=" + encodeURIComponent(strategy), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    loadingEl.style.display = "none";
    if (!resp.ok) {
      document.getElementById("results").innerHTML = `<div class="small">Error: ${JSON.stringify(data)}</div>`;
      return;
    }
    displayResults(data.tasks || []);
    drawGraph(data.tasks || [], data.cycles || []);
    drawMatrix(data.tasks || []);
  } catch (err) {
    loadingEl.style.display = "none";
    document.getElementById("results").innerHTML = `<div class="small">Network error</div>`;
  }
});

function displayResults(tasks) {
  if (!tasks.length) {
    document.getElementById("results").innerHTML = "<div class='small'>No tasks returned</div>";
    return;
  }
  const html = tasks.map(t => {
    const cls = t.score >= 0.7 ? "priority-high" : (t.score >= 0.4 ? "priority-medium" : "priority-low");
    return `<div class="task-card ${cls}">
      <strong>${t.title}</strong>
      <span class="small">score: ${t.score}</span>
      <div class="small">id: ${t.id} | due: ${t.due_date||'—'} |
      hours: ${t.estimated_hours} | importance: ${t.importance}</div>
      <div class="small">why: ${t.reason}</div>
      <div style="margin-top:6px;">
        <button class="feedback-btn" data-id="${t.id}" data-helpful="true">👍 Helpful</button>
        <button class="feedback-btn" data-id="${t.id}" data-helpful="false">👎 Not helpful</button>
      </div>
    </div>`;
  }).join("");
  document.getElementById("results").innerHTML = `<h3>Sorted Tasks</h3>${html}`;

  // attach feedback listeners
  document.querySelectorAll(".feedback-btn").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const id = btn.getAttribute("data-id");
      const helpful = btn.getAttribute("data-helpful") === "true";
      btn.disabled = true;
      try {
        const r = await fetch("http://127.0.0.1:8000/api/tasks/feedback/", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({task_id: id, helpful: helpful})
        });
        const res = await r.json();
        if (r.ok) {
          btn.innerText = helpful ? "👍 Thanks" : "👎 Noted";
        } else {
          btn.innerText = "Error";
        }
      } catch (err) {
        btn.innerText = "Network error";
      }
    });
  });
}

/* drawGraph and drawMatrix functions (copy these into file or ensure they exist) */

function drawGraph(tasks, cycles) {
  // uses d3 available in index.html
  const svg = d3.select("#graph").html("")
    .append("svg").attr("width", 600).attr("height", 300);

  const nodes = tasks.map(t => ({ id: t.id }));
  const links = [];
  tasks.forEach(t => {
    (t.dependencies || []).forEach(d =>
      links.push({ source: d, target: t.id })
    );
  });

  const color = d => (cycles && cycles.some(cycle => cycle.includes(d.id))) ? "red" : "#4CAF50";

  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(80))
    .force("charge", d3.forceManyBody().strength(-200))
    .force("center", d3.forceCenter(300, 150));

  const link = svg.append("g").selectAll("line").data(links).enter()
    .append("line").attr("stroke", "#999").attr("stroke-width", 1.5);

  const node = svg.append("g").selectAll("circle").data(nodes).enter()
    .append("circle").attr("r", 12).attr("fill", color)
    .call(drag(simulation));

  const text = svg.append("g").selectAll("text").data(nodes).enter()
    .append("text").text(d => d.id).attr("dx", 15).attr("dy", 5).style("font-size","11px");

  simulation.on("tick", () => {
    link.attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

    node.attr("cx", d => d.x).attr("cy", d => d.y);
    text.attr("x", d => d.x).attr("y", d => d.y);
  });

  function drag(sim) {
    return d3.drag()
      .on("start", e => { if (!e.active) sim.alphaTarget(0.3).restart(); })
      .on("drag", e => { e.subject.x = e.x; e.subject.y = e.y; })
      .on("end", e => { if (!e.active) sim.alphaTarget(0); });
  }
}

function drawMatrix(tasks) {
  const matrix = document.getElementById("matrix");
  if (!matrix) return;
  matrix.innerHTML = ""; 
  matrix.style.position = "relative";
  // grid background
  matrix.innerHTML = `
    <div style="position:absolute;left:0;top:0;width:50%;height:50%;border-right:1px solid #ccc;border-bottom:1px solid #ccc;padding:8px;">
      <strong>Do First (Urgent & Important)</strong>
    </div>
    <div style="position:absolute;left:50%;top:0;width:50%;height:50%;border-bottom:1px solid #ccc;padding:8px;">
      <strong>Schedule (Not Urgent & Important)</strong>
    </div>
    <div style="position:absolute;left:0;top:50%;width:50%;height:50%;border-right:1px solid #ccc;padding:8px;">
      <strong>Delegate (Urgent & Not Important)</strong>
    </div>
    <div style="position:absolute;left:50%;top:50%;width:50%;height:50%;padding:8px;">
      <strong>Eliminate (Not Urgent & Not Important)</strong>
    </div>
  `;

  const now = new Date();
  function urgencyScore(due) {
    if (!due) return 1000;
    const delta = (new Date(due) - now) / (1000*3600*24);
    return delta; // smaller => more urgent
  }
  tasks.forEach(t => {
    const isUrgent = urgencyScore(t.due_date) <= 3; // due within 3 days => urgent
    const isImportant = (t.importance || 0) >= 7;
    let left = isImportant ? 0 : 50;
    let top = isUrgent ? 0 : 50;
    const box = document.createElement("div");
    box.className = "matrix-task";
    box.innerText = `${t.id} (${t.title})`;
    box.style = `
      position:absolute;
      left:${left+2}%;
      top:${top+12}%;
      background:#3f51b5;
      color:white;
      padding:6px 8px;
      border-radius:6px;
      font-size:12px;
      max-width:45%;
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
    `;
    matrix.appendChild(box);
  });
}
