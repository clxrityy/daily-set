export function show(msg) {
  const el = document.getElementById("messages") || ensureMessagesEl();
  el.textContent = msg;
}

function ensureMessagesEl() {
  let el = document.getElementById("messages");
  if (!el) {
    el = document.createElement("div");
    el.id = "messages";
    el.style.border = "1px solid #ddd";
    el.style.padding = "8px";
    el.style.margin = "12px 0";
    el.innerHTML = "<strong>Messages</strong>";
    const board = document.getElementById("board");
    board?.parentNode?.insertBefore(el, board) || document.body.appendChild(el);
  }
  return el;
}

export function appendEvent(e) {
  console.log("appendEvent called with:", e); // Debug log

  const list = document.getElementById("events-list");
  if (!list) {
    console.error("events-list element not found");
    return;
  }

  console.log("Adding event to events list"); // Debug log

  const row = document.createElement("div");
  row.className = "event-row";
  const time = document.createElement("div");
  time.className = "event-time";
  time.textContent = new Date().toLocaleTimeString();
  const badge = document.createElement("div");
  badge.className = "username-badge";
  badge.textContent = e.username || "anon";
  const text = document.createElement("div");
  text.className = "event-text";

  if (e.type === "completion") {
    text.textContent = `🎉 ${badge.textContent} completed in ${e.seconds}s`;
    setTimeout(() => {
      const leaderboardBtn = document.getElementById("show-leaderboard");
      if (leaderboardBtn) {
        const leaderboard = document.getElementById("leaderboard");
        if (leaderboard && leaderboard.innerHTML.trim() !== "") {
          leaderboardBtn.click();
        }
      }
    }, 500);
  } else if (e.type === "daily_update") {
    text.textContent = `🆕 New daily set is live!`;
    badge.style.display = "none";
  } else if (e.type === "leaderboard_change") {
    text.textContent = `🏅 ${badge.textContent} moved up on the leaderboard!`;
  } else if (e.msg) {
    text.textContent = e.msg;
  } else {
    text.textContent = JSON.stringify(e);
  }

  row.appendChild(time);
  row.appendChild(badge);
  row.appendChild(text);
  list.prepend(row);
}

export function renderSkeletonBoard() {
  const container = document.getElementById("board");
  container.innerHTML = "";

  // Create 12 skeleton cards
  for (let i = 0; i < 12; i++) {
    const skeleton = document.createElement("div");
    skeleton.className = "card skeleton";
    skeleton.innerHTML = `
      <div class="skeleton-content">
        <div class="skeleton-symbols">
          <div class="skeleton-symbol"></div>
          <div class="skeleton-symbol"></div>
          <div class="skeleton-symbol"></div>
        </div>
      </div>
    `;
    container.appendChild(skeleton);
  }
}

function updateCountdown() {
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(0, 0, 0, 0);

  const timeLeft = tomorrow.getTime() - now.getTime();
  const hours = Math.floor(timeLeft / (1000 * 60 * 60));
  const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);

  const countdownEl = document.getElementById("countdown");
  if (countdownEl) {
    countdownEl.textContent = `Time left: ${hours
      .toString()
      .padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds
      .toString()
      .padStart(2, "0")}`;
  }
}

export function startCountdownTimer() {
  updateCountdown();
  return setInterval(updateCountdown, 1000);
}

export async function loadDaily() {
  const resp = await fetch("/api/daily");
  if (!resp.ok) throw new Error("daily load failed");
  const j = await resp.json();
  return j.board;
}

export function renderLeaderboard(j) {
  const el = document.getElementById("leaderboard");
  if (!el) return;
  el.innerHTML =
    `<h3>Leaderboard ${j.date}</h3>` +
    (j.leaders.length
      ? "<ol>" +
        j.leaders.map((l) => `<li>${l.username} — ${l.best}s</li>`).join("") +
        "</ol>"
      : "<div>No results</div>");
}

export function wireControls({ onStartGame }) {
  document.getElementById("start-game")?.addEventListener("click", onStartGame);
  document
    .getElementById("show-leaderboard")
    ?.addEventListener("click", async () => {
      const leaderboardEl = document.getElementById("leaderboard");
      const buttonEl = document.getElementById("show-leaderboard");

      // Check if leaderboard is currently visible (has content)
      const isVisible = leaderboardEl && leaderboardEl.innerHTML.trim() !== "";

      if (isVisible) {
        // Hide leaderboard
        leaderboardEl.innerHTML = "";
        buttonEl.textContent = "Show Leaderboard";
      } else {
        // Show leaderboard
        const resp = await fetch("/api/leaderboard");
        const j = await resp.json();
        renderLeaderboard(j);
        buttonEl.textContent = "Hide Leaderboard";
      }
    });
}
