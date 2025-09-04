let socket;
const listeners = new Set();
export function initWS() {
  const url =
    (location.protocol === "https:" ? "wss://" : "ws://") +
    location.host +
    "/ws";
  console.log("Connecting to WebSocket:", url);
  socket = new WebSocket(url);

  socket.addEventListener("open", () => {
    console.log("WebSocket connected");
  });

  socket.addEventListener("message", (ev) => {
    console.log("WebSocket message received:", ev.data);
    let data;
    try {
      data = JSON.parse(ev.data);
    } catch (e) {
      console.error(
        "Failed to parse WebSocket message as JSON:",
        e,
        "raw data:",
        ev.data
      );
      data = ev.data;
    }
    for (const l of listeners) l(data);
  });

  socket.addEventListener("close", () => {
    console.log("WebSocket closed, reconnecting in 2s");
    setTimeout(initWS, 2000);
  });

  socket.addEventListener("error", (error) => {
    console.error("WebSocket error:", error);
  });
}

export function onWS(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function sendWS(obj) {
  if (socket && socket.readyState === WebSocket.OPEN)
    socket.send(JSON.stringify(obj));
}
