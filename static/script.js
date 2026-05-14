// Wait for MathLive's custom element to be registered
await customElements.whenDefined("math-field");

// ── DOM references ────────────────────────────────────────────
const mathInput     = document.getElementById("math-input");
const limitPoint    = document.getElementById("limit-point");
const limitControls = document.getElementById("limit-controls");
const solveBtn      = document.getElementById("solve-btn");
const similarBtn    = document.getElementById("similar-btn");
const clearBtn      = document.getElementById("clear-btn");
const errorMsg      = document.getElementById("error-msg");
const resultCard    = document.getElementById("result-card");
const similarCard   = document.getElementById("similar-card");
const resultProblem = document.getElementById("result-problem");
const resultAnswer  = document.getElementById("result-answer");
const stepsList     = document.getElementById("steps-list");
const similarGrid   = document.getElementById("similar-grid");
const historyList   = document.getElementById("history-list");

// ── MathLive configuration ─────────────────────────────────────
mathInput.mathVirtualKeyboardPolicy = "onfocus";
limitPoint.mathVirtualKeyboardPolicy = "onfocus";
mathInput.placeholder = "Type your expression…";
limitPoint.placeholder = "0";

// ── Show/hide limit controls when operation type changes ──────
document.querySelectorAll('input[name="op-type"]').forEach(radio => {
  radio.addEventListener("change", () => {
    limitControls.style.display = radio.value === "limit" ? "block" : "none";
  });
});

// ── Helpers ───────────────────────────────────────────────────

function getOpType() {
  return document.querySelector('input[name="op-type"]:checked').value;
}

function renderMath(el, latex) {
  try {
    katex.render(latex, el, { throwOnError: false, displayMode: false });
  } catch {
    el.textContent = latex;
  }
}

/** Convert **bold** and $inline math$ inside a string to HTML. */
function processStepHtml(raw) {
  // Bold markdown
  let html = raw.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  return html;
}

function renderSteps(steps) {
  stepsList.innerHTML = "";
  steps.forEach(step => {
    const li = document.createElement("li");
    li.innerHTML = processStepHtml(step);
    stepsList.appendChild(li);
  });
  // Let KaTeX auto-render find $...$ in the step list
  renderMathInElement(stepsList, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "$",  right: "$",  display: false },
    ],
    throwOnError: false,
  });
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.style.display = "block";
}

function clearError() {
  errorMsg.textContent = "";
  errorMsg.style.display = "none";
}

function setLoading(on) {
  if (on) {
    solveBtn.classList.add("loading");
    solveBtn.innerHTML = '<span class="spinner"></span>Solving…';
  } else {
    solveBtn.classList.remove("loading");
    solveBtn.textContent = "Solve";
  }
}

// ── Solve ─────────────────────────────────────────────────────

solveBtn.addEventListener("click", async () => {
  const expr = mathInput.getValue("latex").trim();
  if (!expr) { showError("Please enter an expression first."); return; }
  clearError();
  setLoading(true);

  const opType = getOpType();
  const payload = { expr, type: opType };
  if (opType === "limit") {
    payload.point     = limitPoint.getValue("latex").trim() || "0";
    payload.direction = document.querySelector('input[name="limit-dir"]:checked').value;
  }

  try {
    const res = await fetch("/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || "Unknown error from server.");
      return;
    }

    // Show result card
    resultCard.style.display = "block";
    renderMath(resultProblem, data.problem_latex);
    renderMath(resultAnswer,  data.result_latex);
    renderSteps(data.steps);
    resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // Refresh history
    await loadHistory();
  } catch (err) {
    showError(`Network error: ${err.message}`);
  } finally {
    setLoading(false);
  }
});

// ── Generate Similar ──────────────────────────────────────────

similarBtn.addEventListener("click", async () => {
  const expr = mathInput.getValue("latex").trim();
  if (!expr) { showError("Please enter an expression first."); return; }
  clearError();

  const opType = getOpType();
  const payload = { expr, type: opType };
  if (opType === "limit") {
    payload.point     = limitPoint.getValue("latex").trim() || "0";
    payload.direction = document.querySelector('input[name="limit-dir"]:checked').value;
  }

  try {
    const res = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok || data.error) { showError(data.error || "Error generating problems."); return; }
    if (!data.problems || data.problems.length === 0) { showError("Could not generate similar problems for this expression."); return; }

    similarCard.style.display = "block";
    similarGrid.innerHTML = "";
    data.problems.forEach(p => {
      const chip = document.createElement("div");
      chip.className = "similar-chip";
      // Wrap in op notation for display
      const displayLatex = data.type === "derivative"
        ? `\\frac{d}{dx}\\left[${p}\\right]`
        : `\\int ${p}\\, dx`;
      try {
        katex.render(displayLatex, chip, { throwOnError: false, displayMode: false });
      } catch {
        chip.textContent = p;
      }
      // Clicking loads the raw expression into the math field
      chip.addEventListener("click", () => {
        mathInput.setValue(p);
        mathInput.focus();
        clearError();
      });
      similarGrid.appendChild(chip);
    });

    similarCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    showError(`Network error: ${err.message}`);
  }
});

// ── Clear ─────────────────────────────────────────────────────

clearBtn.addEventListener("click", () => {
  mathInput.setValue("");
  limitPoint.setValue("");
  mathInput.focus();
  clearError();
  resultCard.style.display  = "none";
  similarCard.style.display = "none";
});

// ── History ───────────────────────────────────────────────────

async function loadHistory() {
  try {
    const res = await fetch("/history");
    const entries = await res.json();
    renderHistory(entries);
  } catch {
    // Non-fatal — history panel just won't update
  }
}

function renderHistory(entries) {
  if (!entries || entries.length === 0) {
    historyList.innerHTML = '<p class="empty-state">No problems solved yet.</p>';
    return;
  }

  historyList.innerHTML = "";
  entries.forEach(e => {
    const item = document.createElement("div");
    item.className = "history-item";

    // Type badge
    const badge = document.createElement("div");
    badge.className = "history-item-type";
    badge.textContent = e.type === "derivative" ? "Derivative" : "Integral";

    // Problem display
    const problem = document.createElement("div");
    problem.className = "history-item-problem";
    try {
      katex.render(e.problem_latex, problem, { throwOnError: false, displayMode: false });
    } catch {
      problem.textContent = e.problem_latex;
    }

    // Timestamp
    const time = document.createElement("div");
    time.className = "history-item-time";
    time.textContent = formatTime(e.created);

    // Delete button
    const del = document.createElement("button");
    del.className = "history-delete";
    del.title = "Remove from history";
    del.textContent = "✕";
    del.addEventListener("click", async ev => {
      ev.stopPropagation();
      await fetch(`/history/${e.id}`, { method: "DELETE" });
      await loadHistory();
    });

    item.appendChild(badge);
    item.appendChild(problem);
    item.appendChild(time);
    item.appendChild(del);

    // Clicking re-shows the result
    item.addEventListener("click", () => showHistoryResult(e));

    historyList.appendChild(item);
  });
}

function showHistoryResult(e) {
  // Load expression back into math field
  mathInput.setValue(e.expr_input);

  // Sync op-type radio
  const radio = document.querySelector(`input[name="op-type"][value="${e.type}"]`);
  if (radio) {
    radio.checked = true;
    limitControls.style.display = e.type === "limit" ? "block" : "none";
  }

  // Restore limit fields if applicable
  if (e.type === "limit" && e.limit_point) {
    limitPoint.setValue(e.limit_point);
    const dirRadio = document.querySelector(
      `input[name="limit-dir"][value="${e.limit_direction || "both"}"]`
    );
    if (dirRadio) dirRadio.checked = true;
  }

  // Show result card
  resultCard.style.display = "block";
  renderMath(resultProblem, e.problem_latex);
  renderMath(resultAnswer,  e.result_latex);
  renderSteps(e.steps);
  clearError();
  resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
}

function formatTime(isoStr) {
  try {
    const d = new Date(isoStr);
    return d.toLocaleString(undefined, {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return isoStr;
  }
}

// ── Submit on Enter (Ctrl/Cmd+Enter) ─────────────────────────

mathInput.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    solveBtn.click();
  }
});

// ── Boot ─────────────────────────────────────────────────────
loadHistory();
mathInput.focus();
