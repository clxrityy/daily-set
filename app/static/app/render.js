import { state } from "./state.js";
import { createSymbolSVG } from "./svg.js";

export function renderBoard(b) {
  state.board = b;
  state.selected = [];
  const container = document.getElementById("board");
  container.innerHTML = "";
  b.forEach((c, i) => {
    const d = document.createElement("div");
    d.className = "card";
    d.dataset.index = i;
    d.tabIndex = 0;
    d.setAttribute("role", "button");
    d.setAttribute("aria-pressed", "false");
    const symbols = document.createElement("div");
    symbols.className = "symbols";
    const [shape, colorIdx, shading, number] = c;
    for (let n = 0; n < number; n++) {
      const svg = createSymbolSVG(shape, colorIdx, shading);
      svg.classList.add("symbol");
      symbols.appendChild(svg);
    }
    d.appendChild(symbols);
    d.addEventListener("click", (e) => {
      const card = e.currentTarget || d;
      const idx = parseInt(card.dataset.index, 10);
      toggleSelect(idx, card);
    });
    d.addEventListener("keydown", (ev) => handleCardKey(ev, i, d));
    container.appendChild(d);
  });
}

import { submitSet } from "./api.js";

export function toggleSelect(i, el) {
  const idx = state.selected.indexOf(i);
  if (idx !== -1) {
    state.selected.splice(idx, 1);
    el.classList.remove("sel");
    el.setAttribute("aria-pressed", "false");
  } else {
    if (state.selected.length >= 3) return;
    state.selected.push(i);
    el.classList.add("sel");
    el.setAttribute("aria-pressed", "true");
  }
  if (state.selected.length === 3) {
    checkSet();
  }
}

function handleCardKey(ev, index, el) {
  if (ev.key === "Enter" || ev.key === " ") {
    ev.preventDefault();
    toggleSelect(index, el);
    return;
  }
  if (!ev.key.startsWith("Arrow")) return;
  const boardEl = document.getElementById("board");
  const cards = boardEl ? Array.from(boardEl.querySelectorAll(".card")) : [];
  if (!cards.length) return;
  const gap = 8;
  const cardW = el.offsetWidth + gap;
  const cols = Math.max(1, Math.round(boardEl.clientWidth / cardW));
  const maxIndex = cards.length - 1;
  const deltas = {
    ArrowRight: 1,
    ArrowLeft: -1,
    ArrowDown: cols,
    ArrowUp: -cols,
  };
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const delta = deltas[ev.key] || 0;
  const target = clamp(index + delta, 0, maxIndex);
  if (target === index) return;
  ev.preventDefault();
  const t = cards[target];
  if (t) t.focus();
}

async function checkSet() {
  const username = document.getElementById("username")?.value || null;
  const seconds = state.startAt
    ? Math.floor((Date.now() - state.startAt) / 1000)
    : null;
  try {
    const res = await submitSet({
      username,
      indices: state.selected,
      seconds,
      session_id: state.sessionId,
      session_token: state.sessionToken,
    });
    if (!res.ok) {
      handleServerError(res);
      return;
    }
    handleSuccess();
  } catch (err) {
    console.error("checkSet error", err);
  }
}

function handleServerError(res) {
  const detail = res.data?.detail ? res.data.detail : JSON.stringify(res.data);
  const el = document.getElementById("messages");
  if (el) el.textContent = "Server: " + detail;
  // clear selection
  state.selected = [];
  document
    .querySelectorAll(".card.sel")
    .forEach((n) => n.classList.remove("sel"));
}

function handleSuccess() {
  const board = state.board;
  state.selected
    .slice()
    .sort((x, y) => y - x)
    .forEach((i) => board.splice(i, 1));
  renderBoard(board);
  checkCompletion(board);
}

function checkCompletion(board) {
  // Check if there are any valid sets remaining
  if (!hasValidSets(board)) {
    stopTimerAndShowCompletion();
    const el = document.getElementById("messages");
    if (el)
      el.textContent = `🎉 Puzzle completed in ${formatTimeSinceStart()}!`;

    // Automatically refresh the leaderboard to show the new completion
    setTimeout(() => {
      const leaderboardBtn = document.getElementById("show-leaderboard");
      if (leaderboardBtn) {
        // Only refresh if leaderboard is currently visible
        const leaderboard = document.getElementById("leaderboard");
        if (leaderboard && leaderboard.innerHTML.trim() !== "") {
          leaderboardBtn.click();
        }
      }
    }, 1000); // Small delay to allow server processing
  }
}

// Check if the given three cards form a valid set
function isValidSet(card1, card2, card3) {
  // For each attribute (shape, color, shading, number), all three cards must have
  // all the same value or all different values
  for (let i = 0; i < 4; i++) {
    const values = [card1[i], card2[i], card3[i]];
    const uniqueValues = new Set(values);
    // Must be all same (1 unique value) or all different (3 unique values)
    if (uniqueValues.size === 2) {
      return false;
    }
  }
  return true;
}

// Check if there are any valid sets remaining on the board
function hasValidSets(board) {
  if (board.length < 3) {
    return false;
  }

  // Check all possible combinations of 3 cards
  for (let i = 0; i < board.length - 2; i++) {
    for (let j = i + 1; j < board.length - 1; j++) {
      for (let k = j + 1; k < board.length; k++) {
        if (isValidSet(board[i], board[j], board[k])) {
          return true;
        }
      }
    }
  }
  return false;
}

function stopTimerAndShowCompletion() {
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
  const elapsed = state.startAt
    ? Math.floor((Date.now() - state.startAt) / 1000)
    : 0;

  // Ensure we don't show negative time
  const finalTime = Math.max(0, elapsed);
  const minutes = Math.floor(finalTime / 60);
  const seconds = finalTime % 60;
  const timerEl = document.getElementById("timer");
  if (timerEl) {
    timerEl.textContent = `Completed in ${minutes}:${seconds
      .toString()
      .padStart(2, "0")}!`;
    timerEl.style.color = "#16a34a"; // green color
    timerEl.style.fontWeight = "bold";
  }
}

function formatTimeSinceStart() {
  const elapsed = state.startAt
    ? Math.floor((Date.now() - state.startAt) / 1000)
    : 0;

  // Ensure we don't show negative time
  const finalTime = Math.max(0, elapsed);
  const minutes = Math.floor(finalTime / 60);
  const seconds = finalTime % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
