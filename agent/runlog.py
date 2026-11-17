"""JSONL run log: one file per run in logs/<YYYY-MM-DD>/, one JSON object per line."""

import json
import uuid
from datetime import datetime, timezone

from .config import REPO_ROOT

LOG_DIR = REPO_ROOT / "logs"


class RunLog:
    def __init__(self, model: str):
        self.run_id = uuid.uuid4().hex
        self.model = model
        now = datetime.now()
        day_dir = LOG_DIR / now.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        self.path = day_dir / f"{now.strftime('%H%M%S')}_{self.run_id[:8]}.jsonl"

    def write(self, event: str, *, ok: bool = True, duration_ms: float | None = None,
              tool: str | None = None, args: dict | None = None, **extra) -> None:
        """event is one of: user_task, tool_call, tool_result, final, error."""
        record = {
            "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds"),
            "run_id": self.run_id,
            "event": event,
            "tool": tool,
            "args": args,
            "ok": ok,
            "model": self.model,
            "duration_ms": None if duration_ms is None else round(duration_ms, 1),
            **extra,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
