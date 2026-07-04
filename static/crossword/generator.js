"use strict";

// In-memory model mirrors the server. cells/blocks are the source of truth;
// the clues map is keyed by "<number><direction>" at current numbering.
const CW = window.CROSSWORD;
const ACROSS = "A";
const DOWN = "D";

const state = {
  cells: CW.cells.slice(),
  blocks: new Set(CW.blocks),
  clues: Object.assign({}, CW.clues), // "1A" -> text, seeded from saved entries
  cursor: 0, // focused cell index
  direction: ACROSS,
};

let dirty = false;
function markDirty() { dirty = true; }

const SVG_NS = "http://www.w3.org/2000/svg";
const svg = document.getElementById("grid");
const rows = CW.numRows;
const cols = CW.numCols;

const idx = (r, c) => r * cols + c;
const rowOf = (i) => Math.floor(i / cols);
const colOf = (i) => i % cols;
const isWhite = (r, c) =>
  r >= 0 && r < rows && c >= 0 && c < cols && !state.blocks.has(idx(r, c));

// --- Slot detection: a direct port of grid.py's slots(). Must stay in sync. ---
function computeSlots() {
  const out = [];
  let number = 0;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (!isWhite(r, c)) continue;
      const startsAcross = !isWhite(r, c - 1) && isWhite(r, c + 1);
      const startsDown = !isWhite(r - 1, c) && isWhite(r + 1, c);
      if (!startsAcross && !startsDown) continue;
      number += 1;
      const start = idx(r, c);
      if (startsAcross) {
        const indices = [];
        let cc = c;
        while (isWhite(r, cc)) indices.push(idx(r, cc++));
        out.push({ number, direction: ACROSS, start, indices });
      }
      if (startsDown) {
        const indices = [];
        let rr = r;
        while (isWhite(rr, c)) indices.push(idx(rr++, c));
        out.push({ number, direction: DOWN, start, indices });
      }
    }
  }
  return out;
}

// Number shown in a cell (if it begins any slot), as a map index -> number.
function cellNumbers(slots) {
  const m = {};
  for (const s of slots) m[s.start] = s.number;
  return m;
}

function slotAt(cellIndex, direction, slots) {
  return slots.find(
    (s) => s.direction === direction && s.indices.includes(cellIndex)
  );
}

function nextSlot(forward, slots) {
  const dirSlots = slots.filter(s => s.direction === state.direction);
  if (!dirSlots.length) return null;
  const current = slotAt(state.cursor, state.direction, slots);
  if (!current) {
    const slot = forward ? dirSlots[0] : dirSlots[dirSlots.length - 1];
    return { slot, direction: state.direction };
  }
  const currentIdx = dirSlots.indexOf(current);
  if (forward) {
    if (currentIdx < dirSlots.length - 1) {
      return { slot: dirSlots[currentIdx + 1], direction: state.direction };
    }
    const otherDir = state.direction === ACROSS ? DOWN : ACROSS;
    const otherSlots = slots.filter(s => s.direction === otherDir);
    return otherSlots.length ? { slot: otherSlots[0], direction: otherDir } : null;
  } else {
    if (currentIdx > 0) {
      return { slot: dirSlots[currentIdx - 1], direction: state.direction };
    }
    const otherDir = state.direction === ACROSS ? DOWN : ACROSS;
    const otherSlots = slots.filter(s => s.direction === otherDir);
    return otherSlots.length
      ? { slot: otherSlots[otherSlots.length - 1], direction: otherDir }
      : null;
  }
}

// --- Rendering ---
function render() {
  const slots = computeSlots();
  const numbers = cellNumbers(slots);
  const active = slotAt(state.cursor, state.direction, slots);
  const activeSet = new Set(active ? active.indices : []);

  svg.innerHTML = "";
  for (let i = 0; i < rows * cols; i++) {
    const r = rowOf(i);
    const c = colOf(i);
    const blocked = state.blocks.has(i);

    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("x", c);
    rect.setAttribute("y", r);
    rect.setAttribute("width", 1);
    rect.setAttribute("height", 1);
    rect.setAttribute("class", "cell" + (blocked ? " block" : "") +
      (!blocked && activeSet.has(i) ? " active" : "") +
      (i === state.cursor ? " cursor" : ""));
    rect.dataset.index = i;
    svg.appendChild(rect);

    if (!blocked && numbers[i]) {
      const num = document.createElementNS(SVG_NS, "text");
      num.setAttribute("x", c + 0.05);
      num.setAttribute("y", r + 0.28);
      num.setAttribute("class", "cell-number");
      num.textContent = numbers[i];
      svg.appendChild(num);
    }
    if (!blocked && state.cells[i]) {
      const t = document.createElementNS(SVG_NS, "text");
      t.setAttribute("x", c + 0.5);
      t.setAttribute("y", r + 0.72);
      t.setAttribute("class", "cell-letter");
      t.setAttribute("text-anchor", "middle");
      t.textContent = state.cells[i];
      svg.appendChild(t);
    }
  }
  updateClueEntry(active);
  updateWarning(slots);
  updateCompletionIndicator(slots);
  renderClueList(slots);
}

// --- Clue entry reflects the active slot ---
function slotKey(slot) {
  return slot ? `${slot.number}${slot.direction}` : null;
}

function updateClueEntry(active) {
  const label = document.getElementById("current-slot");
  const input = document.getElementById("clue-input");
  if (!active) {
    label.textContent = "—";
    input.value = "";
    input.disabled = true;
    return;
  }
  label.textContent = slotKey(active);
  input.disabled = false;
  input.value = state.clues[slotKey(active)] || "";
}

document.getElementById("clue-input").addEventListener("input", (e) => {
  const slots = computeSlots();
  const active = slotAt(state.cursor, state.direction, slots);
  if (!active) return;
  const key = slotKey(active);
  if (e.target.value) state.clues[key] = e.target.value;
  else delete state.clues[key];
  markDirty();
  renderClueList(slots); // refresh list only; don't rebuild grid (keeps focus)
  updateCompletionIndicator(slots);
});

// --- Live Across/Down clue list ---
// Shows every slot, its answer (or pattern with blanks) and attached clue, so
// the constructor sees the clues actually attached, not just fetched ones.
function renderClueList(slots) {
  const across = document.getElementById("clue-list-across");
  const down = document.getElementById("clue-list-down");
  across.innerHTML = "";
  down.innerHTML = "";
  for (const s of slots) {
    const key = slotKey(s);
    const answer = s.indices.map((i) => state.cells[i] || "·").join("");
    const clue = state.clues[key] || "";
    const li = document.createElement("li");
    li.value = s.number;
    li.textContent = clue ? `${answer} — ${clue}` : answer;
    if (!clue) li.classList.add("no-clue");
    li.addEventListener("click", () => {
      state.direction = s.direction;
      state.cursor = s.start;
      render();
      svg.focus();
    });
    (s.direction === ACROSS ? across : down).appendChild(li);
  }
}

// --- Completion indicator ---
function updateCompletionIndicator(slots) {
  const el = document.getElementById("completion-indicator");
  const allComplete = slots.length > 0 && slots.every(s => s.indices.every(i => state.cells[i]));
  const allHaveClues = allComplete && slots.every(s => state.clues[slotKey(s)]);
  const done = allComplete && allHaveClues;
  el.textContent = done ? "✓" : "✗";
  el.className = done ? "done" : "pending";
}

// --- Repeat-answer warning (non-blocking) ---
function updateWarning(slots) {
  const seen = {};
  for (const s of slots) {
    const letters = s.indices.map((i) => state.cells[i]);
    if (letters.some((ch) => !ch)) continue; // only complete slots
    const word = letters.join("");
    seen[word] = (seen[word] || 0) + 1;
  }
  const repeats = Object.keys(seen).filter((w) => seen[w] > 1);
  const el = document.getElementById("warning");
  if (repeats.length) {
    el.textContent = "Repeated answer: " + repeats.join(", ");
    el.hidden = false;
  } else {
    el.hidden = true;
  }
}

// --- Navigation and editing ---
// The cursor may occupy any cell, white or black, so the user can move onto a
// block and toggle it with spacebar. Typing into a block is still prevented,
// and slot advance/retreat still follows white runs only.
function setCursor(i) {
  if (i < 0 || i >= rows * cols) return;
  state.cursor = i;
  render();
}

function advance() {
  const r = rowOf(state.cursor);
  const c = colOf(state.cursor);
  const next = state.direction === ACROSS ? idx(r, c + 1) : idx(r + 1, c);
  if (state.direction === ACROSS && c + 1 < cols && isWhite(r, c + 1))
    state.cursor = next;
  else if (state.direction === DOWN && r + 1 < rows && isWhite(r + 1, c))
    state.cursor = next;
}

function retreat() {
  const r = rowOf(state.cursor);
  const c = colOf(state.cursor);
  if (state.direction === ACROSS && c - 1 >= 0 && isWhite(r, c - 1))
    state.cursor = idx(r, c - 1);
  else if (state.direction === DOWN && r - 1 >= 0 && isWhite(r - 1, c))
    state.cursor = idx(r - 1, c);
}

function toggleBlock(i) {
  const partner = rows * cols - 1 - i;
  const willBlock = !state.blocks.has(i);
  const apply = (j) => {
    if (willBlock) {
      state.blocks.add(j);
      state.cells[j] = "";
    } else {
      state.blocks.delete(j);
    }
  };
  apply(i);
  if (CW.nytRules) apply(partner);
  markDirty();
  const pct = (state.blocks.size / (rows * cols) * 100).toFixed(1);
  document.getElementById("blocks-pct").textContent = pct + "% of cells blocked";
}

svg.addEventListener("click", (e) => {
  const target = e.target.closest(".cell");
  if (!target) return;
  const i = Number(target.dataset.index);
  if (!state.blocks.has(i) && i === state.cursor) {
    state.direction = state.direction === ACROSS ? DOWN : ACROSS;
  }
  setCursor(i);
});

svg.addEventListener("keydown", (e) => {
  const r = rowOf(state.cursor);
  const c = colOf(state.cursor);
  if (e.key === " ") {
    e.preventDefault();
    toggleBlock(state.cursor);
    render();
  } else if (e.key === "Backspace") {
    e.preventDefault();
    if (state.cells[state.cursor]) { state.cells[state.cursor] = ""; markDirty(); }
    else retreat();
    render();
  } else if (e.key === "Delete") {
    e.preventDefault();
    if (state.cells[state.cursor]) { state.cells[state.cursor] = ""; markDirty(); }
    else advance();
    render();
  } else if (e.key === "ArrowLeft") {
    e.preventDefault();
    if (c > 0) setCursor(idx(r, c - 1));
    else setCursor(idx((r - 1 + rows) % rows, cols - 1));
  } else if (e.key === "ArrowRight") {
    e.preventDefault();
    if (c < cols - 1) setCursor(idx(r, c + 1));
    else setCursor(idx((r + 1) % rows, 0));
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    if (r > 0) setCursor(idx(r - 1, c));
    else setCursor(idx(rows - 1, (c - 1 + cols) % cols));
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    if (r < rows - 1) setCursor(idx(r + 1, c));
    else setCursor(idx(0, (c + 1) % cols));
  } else if (e.key === ".") {
    e.preventDefault();
    if (!state.blocks.has(state.cursor)) {
      state.direction = state.direction === ACROSS ? DOWN : ACROSS;
      render();
    }
  } else if (e.key === "Tab") {
    e.preventDefault();
    const slots = computeSlots();
    const result = nextSlot(!e.shiftKey, slots);
    if (result) {
      state.cursor = result.slot.start;
      state.direction = result.direction;
      render();
    }
  } else if (e.key === "[") {
    e.preventDefault();
    doFetchAnswers();
  } else if (e.key === "]") {
    e.preventDefault();
    doFetchClues();
  } else if (/^[a-zA-Z]$/.test(e.key) && !e.ctrlKey && !e.metaKey) {
    e.preventDefault();
    if (!state.blocks.has(state.cursor)) {
      state.cells[state.cursor] = e.key.toUpperCase();
      markDirty();
      advance();
      render();
    }
  }
});

// --- Publish status ---
function updatePublishStatus() {
  const val = document.getElementById("cw-published").value;
  const span = document.getElementById("publish-status");
  const btn = document.getElementById("publish-btn");
  const isPublished = val && new Date(val) <= new Date();
  span.textContent = isPublished ? "Published" : "Unpublished";
  span.className = isPublished ? "status-published" : "status-unpublished";
  btn.textContent = isPublished ? "Unpublish" : "Publish";
}

function nowLocalISO() {
  const d = new Date();
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function localISOWithOffset(localIsoStr) {
  const off = -new Date().getTimezoneOffset();
  const sign = off >= 0 ? "+" : "-";
  const pad = n => String(n).padStart(2, "0");
  const offH = pad(Math.floor(Math.abs(off) / 60));
  const offM = pad(Math.abs(off) % 60);
  return `${localIsoStr}:00${sign}${offH}:${offM}`;
}

document.getElementById("publish-btn").addEventListener("click", () => {
  const input = document.getElementById("cw-published");
  const isPublished = input.value && new Date(input.value) <= new Date();
  input.value = isPublished ? "" : nowLocalISO();
  markDirty();
  updatePublishStatus();
});

// --- Save / JSON ---
document.getElementById("save-btn").addEventListener("click", async () => {
  const body = {
    cells: state.cells,
    blocked_out_squares: Array.from(state.blocks).sort((a, b) => a - b),
    name: document.getElementById("cw-name").value,
    description: document.getElementById("cw-description").value,
    authors: document.getElementById("cw-authors").value,
    editors: document.getElementById("cw-editors").value,
    copyright: document.getElementById("cw-copyright").value,
    published: document.getElementById("cw-published").value
      ? localISOWithOffset(document.getElementById("cw-published").value)
      : null,
    clues: state.clues,
  };
  const resp = await fetch(CW.saveUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": CW.csrfToken },
    body: JSON.stringify(body),
  });
  const btn = document.getElementById("save-btn");
  if (resp.ok) { updatePublishStatus(); dirty = false; }
  btn.textContent = resp.ok ? "Saved" : "Save failed";
  setTimeout(() => (btn.textContent = "Save"), 1500);
});

// --- Fetch answers / clues ---
function activeSlot() {
  const slots = computeSlots();
  return slotAt(state.cursor, state.direction, slots);
}

function showResults(title, items, onPick) {
  const pane = document.getElementById("results-pane");
  const list = document.getElementById("results-list");
  document.getElementById("results-title").textContent = title;
  document.getElementById("results-pager").hidden = true;
  list.innerHTML = "";
  if (!items.length) {
    const li = document.createElement("li");
    li.textContent = "No matches";
    list.appendChild(li);
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    li.addEventListener("click", () => onPick(item));
    list.appendChild(li);
  }
  pane.hidden = false;
}

// Tracks the pattern/slot/page behind the answers pane so the pager
// buttons can re-fetch without redoing activeSlot().
let answersQuery = null;

async function loadAnswersPage(page) {
  const slot = answersQuery.slot;
  const resp = await fetch(CW.fetchAnswersUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": CW.csrfToken },
    body: JSON.stringify({
      cells: state.cells,
      blocked_out_squares: Array.from(state.blocks),
      cursor: slot.start,
      direction: slot.direction,
      page,
    }),
  });
  const data = await resp.json();
  answersQuery.page = data.page;
  answersQuery.totalPages = data.total_pages;
  showResults("Answers", data.answers, (word) => {
    slot.indices.forEach((i, k) => (state.cells[i] = word[k]));
    markDirty();
    state.cursor = slot.start;
    render();
  });

  const pager = document.getElementById("results-pager");
  if (data.total_pages > 1) {
    pager.hidden = false;
    document.getElementById("results-page-info").textContent =
      `Page ${data.page} of ${data.total_pages}`;
    document.getElementById("results-prev").disabled = data.page <= 1;
    document.getElementById("results-next").disabled = data.page >= data.total_pages;
  }
}

async function doFetchAnswers() {
  const slot = activeSlot();
  if (!slot) return;
  answersQuery = { slot, page: 1, totalPages: 0 };
  await loadAnswersPage(1);
}

document.getElementById("results-prev").addEventListener("click", () => {
  if (answersQuery && answersQuery.page > 1) loadAnswersPage(answersQuery.page - 1);
});
document.getElementById("results-next").addEventListener("click", () => {
  if (answersQuery && answersQuery.page < answersQuery.totalPages) loadAnswersPage(answersQuery.page + 1);
});

async function doFetchClues() {
  const slot = activeSlot();
  if (!slot) return;
  const letters = slot.indices.map((i) => state.cells[i]);
  const word = letters.some((ch) => !ch) ? "" : letters.join("");
  const url = CW.fetchCluesUrl + "?word=" + encodeURIComponent(word);
  const resp = await fetch(url);
  const data = await resp.json();
  showResults("Clues", data.clues, (clue) => {
    state.clues[slotKey(slot)] = clue;
    markDirty();
    document.getElementById("clue-input").value = clue;
  });
}

document.getElementById("fetch-answers-btn").addEventListener("click", doFetchAnswers);
document.getElementById("fetch-clues-btn").addEventListener("click", doFetchClues);

document.addEventListener("keydown", (e) => {
  if (e.key === "s" && e.ctrlKey) {
    e.preventDefault();
    document.getElementById("save-btn").click();
  } else if (e.key === "g" && e.ctrlKey) {
    e.preventDefault();
    const input = document.getElementById("clue-input");
    if (document.activeElement === input) {
      svg.focus();
    } else if (!input.disabled) {
      input.focus();
    }
  } else if (e.key === "Escape") {
    document.getElementById("results-pane").hidden = true;
  } else if (e.key === "Home" || e.key === "End") {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
    e.preventDefault();
    setCursor(e.key === "Home" ? 0 : rows * cols - 1);
    svg.focus();
  }
});

document.getElementById("clue-input").addEventListener("keydown", (e) => {
  if (e.key === "Tab") {
    e.preventDefault();
    const slots = computeSlots();
    const result = nextSlot(!e.shiftKey, slots);
    if (result) {
      state.cursor = result.slot.start;
      state.direction = result.direction;
      render();
    }
  }
});

document.getElementById("prev-slot-btn").addEventListener("click", () => {
  const slots = computeSlots();
  const result = nextSlot(false, slots);
  if (result) {
    state.cursor = result.slot.start;
    state.direction = result.direction;
    render();
    svg.focus();
  }
});

document.getElementById("next-slot-btn").addEventListener("click", () => {
  const slots = computeSlots();
  const result = nextSlot(true, slots);
  if (result) {
    state.cursor = result.slot.start;
    state.direction = result.direction;
    render();
    svg.focus();
  }
});

render();
updatePublishStatus();
document.getElementById("blocks-pct").textContent =
  (state.blocks.size / (rows * cols) * 100).toFixed(1) + "% of cells blocked";

["cw-name", "cw-authors", "cw-editors", "cw-copyright", "cw-description", "cw-published"].forEach(id => {
  document.getElementById(id).addEventListener("input", markDirty);
});

window.addEventListener("beforeunload", (e) => {
  if (dirty) e.preventDefault();
});

let pendingHref = null;

document.addEventListener("click", (e) => {
  const link = e.target.closest("a");
  if (!link || !dirty) return;
  e.preventDefault();
  pendingHref = link.href;
  document.getElementById("exit-modal").hidden = false;
});

document.getElementById("exit-confirm").addEventListener("click", () => {
  dirty = false;
  window.location.href = pendingHref;
});

document.getElementById("exit-cancel").addEventListener("click", () => {
  document.getElementById("exit-modal").hidden = true;
  pendingHref = null;
});
