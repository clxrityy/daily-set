function generateRandomUsername() {
  const adjectives = [
    "Swift",
    "Quick",
    "Clever",
    "Sharp",
    "Bright",
    "Smart",
    "Fast",
    "Keen",
    "Wise",
    "Bold",
  ];
  const nouns = [
    "Player",
    "Solver",
    "Finder",
    "Hunter",
    "Seeker",
    "Master",
    "Expert",
    "Ace",
    "Pro",
    "Star",
  ];
  const adj = adjectives[Math.floor(Math.random() * adjectives.length)];
  const noun = nouns[Math.floor(Math.random() * nouns.length)];
  const num = Math.floor(Math.random() * 1000);
  return `${adj}${noun}${num}`;
}

export async function startSession() {
  let username = document.getElementById("username")?.value?.trim();

  // Generate random username if none provided
  if (!username) {
    username = generateRandomUsername();
    // Update the input field to show the generated name
    const usernameInput = document.getElementById("username");
    if (usernameInput) {
      usernameInput.value = username;
    }
  }

  const resp = await fetch("/api/start_session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
  if (!resp.ok) throw new Error("startSession failed");
  return resp.json();
}

export async function submitSet(payload) {
  const resp = await fetch("/api/submit_set", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const text = await resp.text();
  try {
    return { ok: resp.ok, data: JSON.parse(text) };
  } catch (e) {
    console.error(
      "submitSet: failed to parse JSON response, returning raw text:",
      e
    );
    return { ok: resp.ok, data: text };
  }
}
