import http from "k6/http";
import { sleep } from "k6";

export const options = {
  vus: 10,
  duration: "30s",
};

export default function () {
  // Adjust BASE based on your local/remote target
  const BASE = __ENV.BASE_URL || "http://127.0.0.1:8000";
  http.get(`${BASE}/health`);
  http.get(`${BASE}/api/status`);
  // Start session anonymously
  http.post(`${BASE}/api/start_session`, JSON.stringify({}), {
    headers: { "Content-Type": "application/json" },
  });
  sleep(1);
}
