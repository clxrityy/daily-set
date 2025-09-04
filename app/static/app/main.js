import { state } from "./state.js";
import { renderBoard } from "./render.js";
import { startSession } from "./api.js";
import { initWS, onWS } from "./ws.js";
import {
  appendEvent,
  renderSkeletonBoard,
  wireControls,
  show,
  startCountdownTimer,
} from "./ui.js";

let countdownInterval = null;
let gameStarted = false;

async function startGame() {
  if (gameStarted) return;

  try {
    show("Starting game...");
    const sess = await startSession();
    state.sessionId = sess.session_id;
    state.sessionToken = sess.session_token;

    if (sess.start_ts) {
      // Handle ISO string timestamp from server
      state.startAt = new Date(sess.start_ts).getTime();
    } else {
      state.startAt = Date.now();
    }

    // Ensure startAt is not in the future
    if (state.startAt > Date.now()) {
      state.startAt = Date.now();
    }

    // Start game timer
    if (state.timer) clearInterval(state.timer);
    state.timer = setInterval(() => {
      if (!state.startAt) return;
      const elapsed = Math.floor((Date.now() - state.startAt) / 1000);

      // Ensure we don't show negative time
      if (elapsed < 0) {
        state.startAt = Date.now();
        return;
      }

      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      const timerEl = document.getElementById("timer");
      if (timerEl) {
        timerEl.textContent = `${minutes.toString().padStart(2, "0")}:${seconds
          .toString()
          .padStart(2, "0")}`;
      }
    }, 500);

    // Load and render the actual board
    const resp = await fetch("/api/daily");
    const j = await resp.json();
    renderBoard(j.board);

    gameStarted = true;
    show("Game started! Find the sets!");

    // Update button text
    const startButton = document.getElementById("start-game");
    if (startButton) {
      startButton.textContent = "Game Active";
      startButton.disabled = true;
    }
  } catch (e) {
    console.error("Failed to start game:", e);
    show("Failed to start game. Please try again.");
  }
}

function initApp() {
  // Start countdown timer immediately
  countdownInterval = startCountdownTimer();

  // Show skeleton board initially
  renderSkeletonBoard();

  // Initialize WebSocket
  initWS();
  onWS((data) => {
    console.log("WebSocket event received:", data);
    appendEvent(data);
  });

  // Test event injection after a short delay
  setTimeout(() => {
    console.log("Injecting test event");
    appendEvent({
      type: "test",
      username: "TestUser",
      msg: "Test event from frontend timeout",
    });
  }, 3000);

  // Auto-trigger backend test event after WebSocket connects
  setTimeout(async () => {
    try {
      console.log("Triggering backend test event");
      const response = await fetch("/api/test_event");
      const result = await response.json();
      console.log("Backend test event result:", result);
    } catch (e) {
      console.error("Failed to trigger backend test event:", e);
    }
  }, 5000);

  // Wire up controls
  wireControls({
    onStartGame: startGame,
  });
}

window.addEventListener("load", initApp);
