"""Entry point: python -m agent "Was steht am 29.10.2026 im Kalender?" """

import sys

from .agent import run_agent
from .config import load_config
from .runlog import RunLog


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('Usage: python -m agent "<question>"', file=sys.stderr)
        return 2
    task = " ".join(sys.argv[1:])

    # Make sure umlauts print correctly on Windows consoles.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    try:
        cfg = load_config()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    log = RunLog(cfg.model)
    try:
        answer = run_agent(task, cfg, log)
    except Exception as exc:
        log.write("error", ok=False, error=f"{type(exc).__name__}: {exc}")
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
