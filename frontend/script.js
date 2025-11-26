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
  const list = tasksLocal.map(t => `<div class="task-card"><strong>${t.title}</strong> <div class="small">id: ${t.id} | due: ${t.due_date||'—'} | hours: ${t.estimated_hours} | importance: ${t.importance}</div></div>`).join("");
  results.innerHTML = `<h3>Local tasks (${tasksLocal.length})</h3>${list}`;
}

document.getElementById("analyze").addEventListener("click", async () => {
  const jsonText = document.getElementById("json-input").value.trim();
  let payload = [];
  if (jsonText) {
    try {
      payload = JSON.parse(jsonText);
      if (!Array.isArray(payload)) { alert("JSON must be an array of tasks"); return; }
    } catch (e) {
      alert("Invalid JSON");
      return;
    }
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
  } catch (err) {
    loadingEl.style.display = "none";
    document.getElementById("results").innerHTML = `<div class="small">Network error</div>`;
  }
});

function displayResults(tasks) {
  if (!tasks.length) { document.getElementById("results").innerHTML = "<div class='small'>No tasks returned</div>"; return; }
  const html = tasks.map(t => {
    const cls = t.score >= 0.7 ? "priority-high" : (t.score >= 0.4 ? "priority-medium" : "priority-low");
    return `<div class="task-card ${cls}">
      <strong>${t.title}</strong> <span class="small">score: ${t.score}</span>
      <div class="small">id: ${t.id} | due: ${t.due_date || '—'} | hours: ${t.estimated_hours} | importance: ${t.importance}</div>
      <div class="small">why: ${t.reason}</div>
    </div>`;
  }).join("");
  document.getElementById("results").innerHTML = `<h3>Sorted Tasks</h3>${html}`;
}
