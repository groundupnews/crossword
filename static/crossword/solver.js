"use strict";

const CW = window.CROSSWORD;
const ACROSS = "A";
const DOWN = "D";

const state = {
  cells: Array(CW.numRows * CW.numCols).fill(""),
  blocks: new Set(CW.blocks),
  cursor: 0,
  direction: ACROSS,
  checked: {}, // index -> "wrong" (permanent once set)
  indicators: {}, // index -> "correct" | "wrong" (cleared on next edit)
  completed: false,
};

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

function slotKey(slot) {
  return slot ? `${slot.number}${slot.direction}` : null;
}

function nextSlot(forward, slots) {
  const dirSlots = slots.filter((s) => s.direction === state.direction);
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
    const otherSlots = slots.filter((s) => s.direction === otherDir);
    return otherSlots.length ? { slot: otherSlots[0], direction: otherDir } : null;
  } else {
    if (currentIdx > 0) {
      return { slot: dirSlots[currentIdx - 1], direction: state.direction };
    }
    const otherDir = state.direction === ACROSS ? DOWN : ACROSS;
    const otherSlots = slots.filter((s) => s.direction === otherDir);
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
    const checkClass = !blocked && state.checked[i] ? " " + state.checked[i] : "";
    rect.setAttribute(
      "class",
      "cell" +
        (blocked ? " block" : "") +
        (!blocked && activeSet.has(i) ? " active" : "") +
        checkClass +
        (i === state.cursor ? " cursor" : "")
    );
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
    if (!blocked && state.indicators[i]) {
      const ind = document.createElementNS(SVG_NS, "text");
      ind.setAttribute("x", c + 0.5);
      ind.setAttribute("y", r + 0.24);
      ind.setAttribute("class", "cell-indicator " + state.indicators[i]);
      ind.setAttribute("text-anchor", "middle");
      ind.textContent = state.indicators[i] === "correct" ? "✓" : "✗";
      svg.appendChild(ind);
    }
  }
  updateClueDisplay(active);
  renderClueList(slots, active);
}

function updateClueDisplay(active) {
  const slotEl = document.getElementById("current-slot");
  const clueEl = document.getElementById("clue-text");
  if (!active) {
    slotEl.textContent = "—";
    clueEl.textContent = "";
    return;
  }
  const key = slotKey(active);
  slotEl.textContent = key;
  clueEl.textContent = CW.clues[key] || "";
}

function renderClueList(slots, active) {
  const across = document.getElementById("clue-list-across");
  const down = document.getElementById("clue-list-down");
  across.innerHTML = "";
  down.innerHTML = "";
  for (const s of slots) {
    const key = slotKey(s);
    const clue = CW.clues[key] || "";
    const li = document.createElement("li");
    li.value = s.number;
    li.textContent = clue || key;
    if (!clue) li.classList.add("no-clue");
    if (active && s.number === active.number && s.direction === active.direction) {
      li.classList.add("active");
    }
    li.addEventListener("click", () => {
      state.direction = s.direction;
      state.cursor = s.start;
      render();
      svg.focus();
    });
    (s.direction === ACROSS ? across : down).appendChild(li);
  }
}

// --- Navigation and editing ---
function setCursor(i) {
  if (i < 0 || i >= rows * cols) return;
  state.cursor = i;
  render();
}

function advance() {
  const r = rowOf(state.cursor);
  const c = colOf(state.cursor);
  if (state.direction === ACROSS) {
    let nc = c + 1;
    while (nc < cols && !isWhite(r, nc)) nc++;
    if (nc < cols) {
      state.cursor = idx(r, nc);
    } else {
      for (let dr = 1; dr <= rows; dr++) {
        const nr = (r + dr) % rows;
        let fc = 0;
        while (fc < cols && !isWhite(nr, fc)) fc++;
        if (fc < cols) { state.cursor = idx(nr, fc); break; }
      }
    }
  } else {
    let nr = r + 1;
    while (nr < rows && !isWhite(nr, c)) nr++;
    if (nr < rows) {
      state.cursor = idx(nr, c);
    } else {
      for (let dc = 1; dc <= cols; dc++) {
        const nc = (c + dc) % cols;
        let fr = 0;
        while (fr < rows && !isWhite(fr, nc)) fr++;
        if (fr < rows) { state.cursor = idx(fr, nc); break; }
      }
    }
  }
}

function retreat() {
  const r = rowOf(state.cursor);
  const c = colOf(state.cursor);
  if (state.direction === ACROSS && c - 1 >= 0 && isWhite(r, c - 1))
    state.cursor = idx(r, c - 1);
  else if (state.direction === DOWN && r - 1 >= 0 && isWhite(r - 1, c))
    state.cursor = idx(r - 1, c);
}

svg.addEventListener("click", (e) => {
  const target = e.target.closest(".cell");
  if (!target) return;
  const i = Number(target.dataset.index);
  if (state.blocks.has(i)) return;
  if (i === state.cursor) {
    state.direction = state.direction === ACROSS ? DOWN : ACROSS;
  }
  setCursor(i);
});

function handleKey(key, shiftKey = false) {
  if (state.completed) return false;
  const r = rowOf(state.cursor);
  const c = colOf(state.cursor);
  if (key === " ") {
    if (!state.blocks.has(state.cursor)) {
      state.cells[state.cursor] = "";
      delete state.indicators[state.cursor];
      clearMessage();
      advance();
      render();
    }
    return true;
  }
  if (key === "Backspace") {
    if (!state.blocks.has(state.cursor)) {
      playClick();
      if (state.cells[state.cursor]) {
        state.cells[state.cursor] = "";
        delete state.indicators[state.cursor];
        clearMessage();
      } else {
        const prev = state.cursor;
        retreat();
        if (state.cursor === prev) {
          const slots = computeSlots();
          const result = nextSlot(false, slots);
          if (result) {
            state.direction = result.direction;
            state.cursor = result.slot.indices[result.slot.indices.length - 1];
          }
        }
      }
      render();
    }
    return true;
  }
  if (key === "Delete") {
    if (!state.blocks.has(state.cursor)) {
      if (state.cells[state.cursor]) {
        state.cells[state.cursor] = "";
        delete state.indicators[state.cursor];
        clearMessage();
      } else {
        advance();
      }
      render();
    }
    return true;
  }
  if (key === "ArrowLeft") {
    let nc = c - 1;
    while (nc >= 0 && !isWhite(r, nc)) nc--;
    if (nc >= 0) {
      setCursor(idx(r, nc));
    } else {
      for (let dr = 1; dr <= rows; dr++) {
        const nr = (r - dr + rows) % rows;
        let lc = cols - 1;
        while (lc >= 0 && !isWhite(nr, lc)) lc--;
        if (lc >= 0) { setCursor(idx(nr, lc)); break; }
      }
    }
    return true;
  }
  if (key === "ArrowRight") {
    let nc = c + 1;
    while (nc < cols && !isWhite(r, nc)) nc++;
    if (nc < cols) {
      setCursor(idx(r, nc));
    } else {
      for (let dr = 1; dr <= rows; dr++) {
        const nr = (r + dr) % rows;
        let fc = 0;
        while (fc < cols && !isWhite(nr, fc)) fc++;
        if (fc < cols) { setCursor(idx(nr, fc)); break; }
      }
    }
    return true;
  }
  if (key === "ArrowUp") {
    let nr = r - 1;
    while (nr >= 0 && !isWhite(nr, c)) nr--;
    if (nr >= 0) {
      setCursor(idx(nr, c));
    } else {
      for (let dc = 1; dc <= cols; dc++) {
        const nc = (c - dc + cols) % cols;
        let lr = rows - 1;
        while (lr >= 0 && !isWhite(lr, nc)) lr--;
        if (lr >= 0) { setCursor(idx(lr, nc)); break; }
      }
    }
    return true;
  }
  if (key === "ArrowDown") {
    let nr = r + 1;
    while (nr < rows && !isWhite(nr, c)) nr++;
    if (nr < rows) {
      setCursor(idx(nr, c));
    } else {
      for (let dc = 1; dc <= cols; dc++) {
        const nc = (c + dc) % cols;
        let fr = 0;
        while (fr < rows && !isWhite(fr, nc)) fr++;
        if (fr < rows) { setCursor(idx(fr, nc)); break; }
      }
    }
    return true;
  }
  if (key === ".") {
    if (!state.blocks.has(state.cursor)) {
      state.direction = state.direction === ACROSS ? DOWN : ACROSS;
      render();
    }
    return true;
  }
  if (key === "Tab") {
    const slots = computeSlots();
    const result = nextSlot(!shiftKey, slots);
    if (result) {
      state.cursor = result.slot.start;
      state.direction = result.direction;
      render();
    }
    return true;
  }
  if (/^[a-zA-Z]$/.test(key)) {
    if (!state.blocks.has(state.cursor)) {
      playClick();
      state.cells[state.cursor] = key.toUpperCase();
      delete state.indicators[state.cursor];
      clearMessage();
      advance();
      render();
      autoCheckIfComplete();
    }
    return true;
  }
  return false;
}

svg.addEventListener("keydown", (e) => {
  if (handleKey(e.key, e.shiftKey)) e.preventDefault();
});

document.querySelectorAll(".kb-key").forEach((btn) => {
  btn.addEventListener("click", () => handleKey(btn.dataset.key));
});

// --- Check feature ---
async function doCheck(mode, markWrong = true) {
  try {
    const resp = await fetch(CW.checkUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": CW.csrfToken,
      },
      body: JSON.stringify({
        mode,
        cells: state.cells,
        cursor: state.cursor,
        direction: state.direction,
      }),
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    for (const { index, correct } of data.results) {
      if (state.cells[index] && markWrong) {
        state.indicators[index] = correct ? "correct" : "wrong";
        if (!correct) state.checked[index] = "wrong";
      }
    }
    render();
    return data.results;
  } catch (_) {
    return null;
  }
}

function isComplete() {
  for (let i = 0; i < rows * cols; i++) {
    if (!state.blocks.has(i) && !state.cells[i]) return false;
  }
  return true;
}

const msgEl = document.getElementById("completion-message");

function showMessage(text, type) {
  msgEl.textContent = text;
  msgEl.className = type;
  msgEl.hidden = false;
}

function clearMessage() {
  msgEl.hidden = true;
}

let soundEnabled = true;

document.getElementById("sound-btn").addEventListener("click", () => {
  soundEnabled = !soundEnabled;
  document.getElementById("sound-btn").textContent = soundEnabled ? "🔊" : "🔇";
});

let _audioCtx = null;
let _clickBuf = null;
const CLICK_DUR = 0.035;

function audioCtx() {
  if (!_audioCtx) {
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)({ latencyHint: 'interactive' });
    const buf = _audioCtx.createBuffer(1, Math.ceil(_audioCtx.sampleRate * CLICK_DUR), _audioCtx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    _clickBuf = buf;
  }
  return _audioCtx;
}

function playClick() {
  if (!soundEnabled) return;
  const ctx = audioCtx();
  const source = ctx.createBufferSource();
  source.buffer = _clickBuf;
  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = 1200;
  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0.5, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + CLICK_DUR);
  source.connect(filter);
  filter.connect(gain);
  gain.connect(ctx.destination);
  source.start(ctx.currentTime);
  source.stop(ctx.currentTime + CLICK_DUR);
}

function playTada() {
  if (!soundEnabled) return;
  const ctx = audioCtx();
  const notes = [
    { freq: 523.25, start: 0,    dur: 0.15 },  // C5
    { freq: 659.25, start: 0.12, dur: 0.15 },  // E5
    { freq: 783.99, start: 0.24, dur: 0.55 },  // G5
  ];
  for (const { freq, start, dur } of notes) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = "triangle";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.28, ctx.currentTime + start);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + dur);
    osc.start(ctx.currentTime + start);
    osc.stop(ctx.currentTime + start + dur);
  }
}

async function autoCheckIfComplete() {
  if (!isComplete()) return;
  const results = await doCheck("crossword", false);
  if (!results) return;
  if (results.every((r) => r.correct)) {
    state.completed = true;
    clearInterval(timerInterval);
    playTada();
    document.getElementById("check-btn").closest(".check-dropdown").style.display = "none";
    document.getElementById("reveal-btn").closest(".check-dropdown").style.display = "none";
    document.getElementById("sound-btn").style.display = "none";
    const totalWhite = rows * cols - state.blocks.size;
    const wrongCount = Object.values(state.checked).filter(v => v === "wrong").length;
    const pct = Math.round((totalWhite - wrongCount) / totalWhite * 100);
    showMessage(`Crossword completed. You scored ${pct}%.`, "success");
  } else {
    showMessage("The crossword has some wrong answers.", "error");
  }
}

const checkBtn = document.getElementById("check-btn");
const checkMenu = document.getElementById("check-menu");

checkBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  checkMenu.hidden = !checkMenu.hidden;
});

checkMenu.addEventListener("click", (e) => {
  const li = e.target.closest("li[data-mode]");
  if (!li) return;
  checkMenu.hidden = true;
  doCheck(li.dataset.mode);
  svg.focus();
});

// --- Reveal feature ---
async function doReveal(mode) {
  const labels = { letter: "this letter", word: "this word", crossword: "the entire crossword" };
  if (!confirm(`Reveal ${labels[mode]}?`)) return;
  try {
    const resp = await fetch(CW.revealUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": CW.csrfToken },
      body: JSON.stringify({ mode, cursor: state.cursor, direction: state.direction }),
    });
    if (!resp.ok) return;
    const data = await resp.json();
    for (const { index, letter } of data.results) {
      if (!letter) continue;
      if (state.cells[index] !== letter) {
        // blank or wrong — count against score
        state.checked[index] = "wrong";
        state.cells[index] = letter;
      }
      delete state.indicators[index];
    }
    render();
    autoCheckIfComplete();
  } catch (_) {}
}

const revealBtn = document.getElementById("reveal-btn");
const revealMenu = document.getElementById("reveal-menu");

revealBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  revealMenu.hidden = !revealMenu.hidden;
});

revealMenu.addEventListener("click", (e) => {
  const li = e.target.closest("li[data-mode]");
  if (!li) return;
  revealMenu.hidden = true;
  doReveal(li.dataset.mode);
  svg.focus();
});

document.addEventListener("click", () => {
  checkMenu.hidden = true;
  revealMenu.hidden = true;
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Home" || e.key === "End") {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
    e.preventDefault();
    setCursor(e.key === "Home" ? 0 : rows * cols - 1);
    svg.focus();
  }
});

// --- Timer ---
let timerSeconds = 0;
const timerEl = document.getElementById("timer");
document.getElementById("timer-toggle").addEventListener("click", () => {
  const hidden = !timerEl.hidden;
  timerEl.hidden = hidden;
  document.getElementById("timer-toggle").textContent = hidden ? "Show" : "Hide";
});

const timerInterval = setInterval(() => {
  timerSeconds++;
  const h = Math.floor(timerSeconds / 3600);
  const m = Math.floor((timerSeconds % 3600) / 60);
  const s = timerSeconds % 60;
  timerEl.textContent = "Time taken: " +
    String(h).padStart(2, "0") + ":" +
    String(m).padStart(2, "0") + ":" +
    String(s).padStart(2, "0");
}, 1000);

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

const _initSlots = computeSlots();
const _firstAcross = _initSlots.find((s) => s.direction === ACROSS);
if (_firstAcross) {
  state.cursor = _firstAcross.start;
  state.direction = ACROSS;
}
render();
svg.focus();
