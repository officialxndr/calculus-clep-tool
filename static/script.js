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
initTabs();
initPractice();
initExam();

// ═════════════════════════════════════════════════════════════
//  TAB SWITCHING
// ═════════════════════════════════════════════════════════════

function initTabs() {
  const tabs   = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".tab-panel");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      tabs.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      panels.forEach(p => p.style.display = "none");
      document.getElementById(`tab-${target}`).style.display = "block";
    });
  });
}

// ═════════════════════════════════════════════════════════════
//  PRACTICE MODE
// ═════════════════════════════════════════════════════════════

let practiceState = {
  question: null,   // current question dict (without correct_index)
  answered: false,
  correct: 0,
  attempted: 0,
};

function initPractice() {
  document.getElementById("practice-next-btn").addEventListener("click", () => loadPracticeQuestion());
  updatePracticeScoreBadge();
}

async function loadPracticeQuestion() {
  const topic = document.getElementById("practice-topic").value;
  const card  = document.getElementById("practice-question-card");

  card.innerHTML = `<p class="empty-state" style="padding:2rem 0">Loading…</p>`;
  practiceState.answered = false;

  try {
    const res  = await fetch(`/practice/question?topic=${encodeURIComponent(topic)}`);
    const data = await res.json();
    if (data.error) { card.innerHTML = `<p class="error-msg">${data.error}</p>`; return; }
    practiceState.question = data;
    renderPracticeQuestion(data);
  } catch (err) {
    card.innerHTML = `<p class="error-msg">Network error: ${err.message}</p>`;
  }
}

function renderPracticeQuestion(q) {
  const card = document.getElementById("practice-question-card");

  const choicesHtml = q.choices.map((c, i) => `
    <div class="mc-option" data-index="${i}" tabindex="0" role="button">
      <span class="mc-label">${c.label}</span>
      <span class="mc-math" data-latex="${escapeAttr(c.latex)}"></span>
    </div>`).join("");

  card.innerHTML = `
    <div class="practice-question-text" id="pq-text"></div>
    <div class="mc-options">${choicesHtml}</div>
    <div class="practice-check-row">
      <button id="pq-check-btn" class="btn btn-primary" disabled>Check Answer</button>
    </div>
    <div id="pq-feedback" style="display:none" class="practice-feedback"></div>`;

  // Render question text
  renderMathInEl(document.getElementById("pq-text"), q.question_latex);

  // Render choice math
  card.querySelectorAll(".mc-math").forEach(el => {
    renderMathInEl(el, el.dataset.latex);
  });

  // Choice selection
  let selectedIdx = null;
  card.querySelectorAll(".mc-option").forEach(opt => {
    opt.addEventListener("click", () => {
      if (practiceState.answered) return;
      card.querySelectorAll(".mc-option").forEach(o => o.classList.remove("selected"));
      opt.classList.add("selected");
      selectedIdx = parseInt(opt.dataset.index, 10);
      document.getElementById("pq-check-btn").disabled = false;
    });
    opt.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") opt.click(); });
  });

  // Check answer
  document.getElementById("pq-check-btn").addEventListener("click", async () => {
    if (selectedIdx === null || practiceState.answered) return;
    practiceState.answered = true;
    practiceState.attempted++;

    try {
      const res = await fetch("/practice/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: q.id, chosen_index: selectedIdx }),
      });
      const data = await res.json();
      if (data.error) return;

      if (data.correct) practiceState.correct++;
      updatePracticeScoreBadge();

      // Highlight choices
      card.querySelectorAll(".mc-option").forEach(opt => {
        const idx = parseInt(opt.dataset.index, 10);
        if (idx === data.correct_index) opt.classList.add("correct");
        else if (idx === selectedIdx && !data.correct) opt.classList.add("wrong");
      });

      // Feedback
      const fb = document.getElementById("pq-feedback");
      fb.className = `practice-feedback ${data.correct ? "correct-fb" : "wrong-fb"}`;
      const icon = data.correct ? "✓" : "✗";
      fb.innerHTML = `<strong>${icon} ${data.correct ? "Correct!" : "Incorrect."}</strong>
        Correct answer: <strong>${data.correct_label}</strong>. `;
      fb.style.display = "block";

      // Explanation as collapsible
      if (data.explanation) {
        const exDiv = document.createElement("div");
        exDiv.style.marginTop = ".6rem";
        exDiv.innerHTML = processStepHtml(data.explanation);
        fb.appendChild(exDiv);
        renderMathInElement(fb, {
          delimiters: [{ left: "$", right: "$", display: false }, { left: "$$", right: "$$", display: true }],
          throwOnError: false,
        });
      }

      // Replace Check button with Next button
      document.getElementById("pq-check-btn").replaceWith(
        Object.assign(document.createElement("button"), {
          className: "btn btn-primary",
          textContent: "Next Question",
          onclick: loadPracticeQuestion,
        })
      );
    } catch (err) {
      console.error(err);
    }
  });
}

function updatePracticeScoreBadge() {
  const { correct, attempted } = practiceState;
  document.getElementById("practice-score-badge").textContent = `${correct} / ${attempted}`;
}

function renderMathInEl(el, latex) {
  try {
    katex.render(latex, el, { throwOnError: false, displayMode: false });
  } catch {
    el.textContent = latex;
  }
}

function escapeAttr(s) {
  return s.replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

// ═════════════════════════════════════════════════════════════
//  MOCK EXAM
// ═════════════════════════════════════════════════════════════

let examState = {
  examId: null,
  questions: [],
  answers: [],   // array of int|null, length = questions.length
  current: 0,
  timerInterval: null,
  secondsLeft: 3600,
};

function initExam() {
  document.getElementById("exam-start-btn").addEventListener("click", startExam);
  document.getElementById("exam-prev-btn").addEventListener("click", () => navigateExam(examState.current - 1));
  document.getElementById("exam-next-btn").addEventListener("click", () => navigateExam(examState.current + 1));
  document.getElementById("exam-submit-btn").addEventListener("click", () => {
    if (confirm(`Submit exam? You have answered ${examState.answers.filter(a => a !== null).length} of ${examState.questions.length} questions.`)) {
      submitExam();
    }
  });
  document.getElementById("exam-retake-btn").addEventListener("click", () => {
    document.getElementById("exam-results").style.display = "none";
    document.getElementById("exam-prescreen").style.display = "flex";
  });
}

async function startExam() {
  const startBtn = document.getElementById("exam-start-btn");
  const loading  = document.getElementById("exam-start-loading");
  startBtn.style.display = "none";
  loading.style.display  = "flex";

  try {
    const res  = await fetch("/exam/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const data = await res.json();
    if (data.error) { alert("Error: " + data.error); return; }

    examState.examId    = data.exam_id;
    examState.questions = data.questions;
    examState.answers   = new Array(data.questions.length).fill(null);
    examState.current   = 0;
    examState.secondsLeft = 3600;

    document.getElementById("exam-prescreen").style.display = "none";
    document.getElementById("exam-screen").style.display    = "block";

    buildPalette();
    renderExamQuestion(0);
    startTimer();
  } catch (err) {
    alert("Network error: " + err.message);
  } finally {
    startBtn.style.display = "block";
    loading.style.display  = "none";
  }
}

function buildPalette() {
  const palette = document.getElementById("exam-palette");
  palette.innerHTML = "";
  examState.questions.forEach((_, i) => {
    const btn = document.createElement("button");
    btn.className = "palette-btn";
    btn.textContent = i + 1;
    btn.addEventListener("click", () => navigateExam(i));
    palette.appendChild(btn);
  });
}

function updatePalette() {
  const btns = document.getElementById("exam-palette").children;
  for (let i = 0; i < btns.length; i++) {
    btns[i].className = "palette-btn";
    if (examState.answers[i] !== null) btns[i].classList.add("answered");
    if (i === examState.current)       btns[i].classList.add("current");
  }
}

function navigateExam(idx) {
  if (idx < 0 || idx >= examState.questions.length) return;
  examState.current = idx;
  renderExamQuestion(idx);
}

function renderExamQuestion(idx) {
  const q = examState.questions[idx];
  const total = examState.questions.length;

  document.getElementById("exam-progress").textContent = `Question ${idx + 1} / ${total}`;
  document.getElementById("exam-prev-btn").disabled = (idx === 0);
  document.getElementById("exam-next-btn").disabled = (idx === total - 1);

  const topicMap = { derivatives: "Derivatives", limits: "Limits", integrals: "Integrals", applications: "Applications" };
  document.getElementById("exam-topic-badge").textContent = topicMap[q.topic] || q.topic;

  const qText = document.getElementById("exam-question-text");
  renderMathInEl(qText, q.question_latex);

  const choicesDiv = document.getElementById("exam-choices");
  choicesDiv.innerHTML = q.choices.map((c, i) => `
    <div class="mc-option${examState.answers[idx] === i ? " selected" : ""}" data-index="${i}" tabindex="0" role="button">
      <span class="mc-label">${c.label}</span>
      <span class="mc-math" data-latex="${escapeAttr(c.latex)}"></span>
    </div>`).join("");

  choicesDiv.querySelectorAll(".mc-math").forEach(el => renderMathInEl(el, el.dataset.latex));

  choicesDiv.querySelectorAll(".mc-option").forEach(opt => {
    opt.addEventListener("click", () => {
      const chosen = parseInt(opt.dataset.index, 10);
      examState.answers[idx] = chosen;
      choicesDiv.querySelectorAll(".mc-option").forEach(o => o.classList.remove("selected"));
      opt.classList.add("selected");
      updatePalette();
    });
    opt.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") opt.click(); });
  });

  updatePalette();
}

function startTimer() {
  if (examState.timerInterval) clearInterval(examState.timerInterval);
  updateTimerDisplay();
  examState.timerInterval = setInterval(() => {
    examState.secondsLeft--;
    updateTimerDisplay();
    if (examState.secondsLeft <= 0) {
      clearInterval(examState.timerInterval);
      alert("Time is up! Submitting your exam now.");
      submitExam();
    }
  }, 1000);
}

function updateTimerDisplay() {
  const m = Math.floor(examState.secondsLeft / 60).toString().padStart(2, "0");
  const s = (examState.secondsLeft % 60).toString().padStart(2, "0");
  const el = document.getElementById("exam-timer");
  el.textContent = `${m}:${s}`;
  if (examState.secondsLeft <= 300) el.classList.add("danger");
  else el.classList.remove("danger");
}

async function submitExam() {
  if (examState.timerInterval) clearInterval(examState.timerInterval);
  document.getElementById("exam-screen").style.display = "none";

  try {
    const res = await fetch("/exam/grade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exam_id: examState.examId, answers: examState.answers }),
    });
    const data = await res.json();
    if (data.error) { alert("Error grading: " + data.error); return; }
    renderExamResults(data);
  } catch (err) {
    alert("Network error: " + err.message);
  }
}

function renderExamResults(data) {
  const resultsEl = document.getElementById("exam-results");
  resultsEl.style.display = "block";

  // Score banner
  const pct = data.percent;
  const banner = document.getElementById("score-banner");
  banner.className = "score-banner " + (pct >= 60 ? "pass-banner" : "fail-banner");
  document.getElementById("score-big").textContent = `${data.score} / ${data.total}`;
  document.getElementById("score-pct").textContent = `${pct}%`;
  document.getElementById("score-label").textContent =
    pct >= 75 ? "Excellent! You passed." :
    pct >= 60 ? "Good effort! You passed." :
    "Keep studying — you've got this!";

  // Topic breakdown
  const table = document.getElementById("topic-table");
  const topicLabel = { derivatives: "Derivatives", limits: "Limits", integrals: "Integrals", applications: "Applications" };
  table.innerHTML = `<tr><th>Topic</th><th>Correct</th><th>Total</th><th>%</th></tr>` +
    Object.entries(data.topic_scores).map(([t, s]) => {
      const tp = s.total ? Math.round(s.correct / s.total * 100) : 0;
      return `<tr><td>${topicLabel[t] || t}</td><td>${s.correct}</td><td>${s.total}</td><td>${tp}%</td></tr>`;
    }).join("");

  // Question review
  const reviewList = document.getElementById("review-list");
  reviewList.innerHTML = "";
  data.results.forEach(r => {
    const item = document.createElement("div");
    item.className = `review-item ${r.is_correct ? "correct-item" : "wrong-item"}`;

    const header = document.createElement("div");
    header.className = "review-item-header";
    header.innerHTML = `
      <span class="review-icon">${r.is_correct ? "✓" : "✗"}</span>
      <span class="review-num">Q${r.question_num}</span>
      <span class="review-q-preview">${r.question_latex.replace(/\$/g, "").substring(0, 60)}…</span>`;

    const body = document.createElement("div");
    body.className = "review-item-body";

    const questionEl = document.createElement("div");
    questionEl.className = "review-answer-row";
    renderMathInEl(questionEl, r.question_latex);

    const yourAnswer = document.createElement("div");
    yourAnswer.className = "review-answer-row";
    yourAnswer.innerHTML = `<span class="review-label">Your answer:</span> `;
    if (r.chosen_label) {
      const mathSpan = document.createElement("span");
      renderMathInEl(mathSpan, `${r.chosen_label}: ${r.chosen_latex || "—"}`);
      yourAnswer.appendChild(mathSpan);
    } else {
      yourAnswer.innerHTML += "<em>Not answered</em>";
    }

    const correctAnswer = document.createElement("div");
    correctAnswer.className = "review-answer-row";
    correctAnswer.innerHTML = `<span class="review-label">Correct:</span> `;
    const correctSpan = document.createElement("span");
    renderMathInEl(correctSpan, `${r.correct_label}: ${r.correct_latex}`);
    correctAnswer.appendChild(correctSpan);

    body.appendChild(questionEl);
    if (!r.is_correct || r.chosen_label) body.appendChild(yourAnswer);
    body.appendChild(correctAnswer);

    if (r.explanation) {
      const exDiv = document.createElement("div");
      exDiv.style.marginTop = ".5rem";
      exDiv.innerHTML = `<span class="review-label">Explanation:</span> ` + processStepHtml(r.explanation);
      body.appendChild(exDiv);
    }

    // Render math in body after building
    renderMathInElement(body, {
      delimiters: [{ left: "$", right: "$", display: false }, { left: "$$", right: "$$", display: true }],
      throwOnError: false,
    });

    header.addEventListener("click", () => body.classList.toggle("open"));
    item.appendChild(header);
    item.appendChild(body);
    reviewList.appendChild(item);
  });

  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}
