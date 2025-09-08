import json
import logging
import os
import sys
import typing as _t
from contextvars import ContextVar
from typing import Any, Dict, Optional

# Context var to carry a request id through the request lifecycle
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """Simple JSON log formatter suitable for app logs and log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = request_id_ctx.get()
        if rid:
            payload["request_id"] = rid
        # Pick up known extra fields added via logger.extra (as attributes on record)
        for key in (
            "path",
            "method",
            "status",
            "duration_ms",
            "client",
            "user_agent",
            "event",
            "ws_count",
            "url",
            "errors",
            "error",
        ):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        # Attach exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class ColorFormatter(logging.Formatter):
    """Human-friendly, colorized formatter that uses structured fields when present."""

    # ANSI colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    COLORS = {
        "DEBUG": "\033[36m",   # cyan
        "INFO": "\033[32m",    # green
        "WARNING": "\033[33m", # yellow
        "ERROR": "\033[31m",   # red
        "CRITICAL": "\033[35m",# magenta
    }

    def __init__(self, use_color: bool = True):
        super().__init__()
        self.use_color = use_color

    def _color(self, text: str, color: str) -> str:
        if not self.use_color:
            return text
        return f"{color}{text}{self.RESET}"

    def _status_str(self, status: Optional[int]) -> Optional[str]:
        if not isinstance(status, int):
            return None
        if 200 <= status < 300:
            return self._color(str(status), "\033[32m")  # green
        if 300 <= status < 400:
            return self._color(str(status), "\033[36m")  # cyan
        if 400 <= status < 500:
            return self._color(str(status), "\033[33m")  # yellow
        return self._color(str(status), "\033[31m")  # red

    def _request_line(self, method: Optional[str], path: Optional[str], status_str: Optional[str], duration_ms: Optional[int]) -> Optional[str]:
        parts: _t.List[str] = []
        if method:
            parts.append(self._color(method, self.BOLD))
        if path:
            parts.append(self._color(path, "\033[36m"))
        if status_str:
            parts.append(status_str)
        if duration_ms is not None:
            parts.append(self._color(f"{duration_ms}ms", "\033[90m"))
        return " ".join(parts) if parts else None

    def _context_str(self, client: Optional[str], ua: Optional[str]) -> Optional[str]:
        ctx: _t.List[str] = []
        if client:
            ctx.append(f"client={client}")
        if ua:
            u = ua if len(ua) <= 64 else ua[:61] + "..."
            ctx.append(f"ua=\"{u}\"")
        return "[" + " ".join(ctx) + "]" if ctx else None

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        ts = self.formatTime(record, datefmt="%H:%M:%S")
        rid = request_id_ctx.get()
        logger_name = record.name

        method = getattr(record, "method", None)
        path = getattr(record, "path", None)
        status = getattr(record, "status", None)
        duration_ms = getattr(record, "duration_ms", None)
        client = getattr(record, "client", None)
        ua = getattr(record, "user_agent", None)
        msg = record.getMessage()

        parts: _t.List[str] = [
            self._color(level, self.COLORS.get(level, "")),
            ts,
        ]
        if rid:
            parts.append(self._color(f"rid={rid}", "\033[35m"))
        parts.append(self._color(logger_name, "\033[34m"))

        req_line = self._request_line(method, path, self._status_str(status), duration_ms)
        if req_line:
            parts.append(req_line)

        if msg:
            parts.extend(["-", msg])

        ctx = self._context_str(client, ua)
        if ctx:
            parts.append(self._color(ctx, "\033[90m"))

        if record.exc_info:
            parts.append("\n" + self.formatException(record.exc_info))

        return " ".join(parts)


def _isatty(stream) -> bool:
    try:
        return hasattr(stream, "isatty") and stream.isatty()
    except Exception:
        return False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure root and uvicorn loggers.

    Chooses JSON (default) or colorized pretty format based on env/TTY:
    - LOG_FORMAT=pretty forces pretty
    - LOG_FORMAT=json forces JSON
    - otherwise: pretty if stdout is a TTY, else JSON
    - LOG_COLOR=0 disables ANSI colors in pretty mode
    """
    root = logging.getLogger()
    root.setLevel(level)
    # Clear existing handlers to avoid duplicate logs
    for h in root.handlers[:]:
        root.removeHandler(h)

    fmt_env = os.getenv("LOG_FORMAT", "").lower()
    color_env = os.getenv("LOG_COLOR", "1").lower()
    use_pretty = (fmt_env == "pretty") or (fmt_env == "" and _isatty(sys.stdout))
    use_color = use_pretty and color_env not in ("0", "false", "no")

    handler = logging.StreamHandler(sys.stdout)
    if use_pretty:
        handler.setFormatter(ColorFormatter(use_color=use_color))
    else:
        handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    # Align uvicorn loggers to the same handler/level
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.setLevel(level)
        lg.propagate = False

    return root


def get_logger(name: str = "app") -> logging.Logger:
    return logging.getLogger(name)
