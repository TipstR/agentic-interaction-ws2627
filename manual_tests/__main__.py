"""Run all manual test questions and write a Markdown report for review by hand.

    python -m manual_tests                 # all questions, today = 2026-10-28
    python -m manual_tests --only 1,5,7    # a subset
    python -m manual_tests --today 2026-11-01
"""

import argparse
import json
import sys
import time
from datetime import date, datetime

from agent.agent import run_agent
from agent.config import REPO_ROOT, load_config
from agent.runlog import RunLog

from .questions import QUESTIONS

REPORT_DIR = REPO_ROOT / "test_runs"
DEFAULT_TODAY = "2026-10-28"  # a Wednesday inside the mock calendar range


def summarize_result(result: dict) -> str:
    if "error" in result:
        return f"error: {result['error']}"
    if result.get("no_data"):
        return "no_data"
    events = result.get("events")
    if isinstance(events, list):
        return f"{len(events)} events"
    return json.dumps(result, ensure_ascii=False)[:80]


def read_log(path) -> dict:
    """Pull tool calls, rounds and errors out of one run's JSONL log."""
    calls, errors, rounds = [], [], 0
    if not path.exists():
        return {"calls": calls, "errors": errors, "rounds": rounds}
    for line in path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        rounds = max(rounds, rec.get("round") or 0)
        if rec["event"] == "tool_result":
            args = rec.get("args") or {}
            arg = args.get("date", json.dumps(args, ensure_ascii=False))
            calls.append(f"{rec['tool']}({arg}) -> {summarize_result(rec.get('result') or {})}")
        elif rec["event"] == "error":
            errors.append(rec.get("error", ""))
    return {"calls": calls, "errors": errors, "rounds": rounds}


def md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def write_report(results: list[dict], model: str, today: date, started: datetime) -> str:
    lines = [
        "# Manual test run",
        "",
        f"- **Model:** `{model}`",
        f"- **Pinned today:** {today.isoformat()} ({today.strftime('%A')})",
        f"- **Started:** {started.isoformat(timespec='seconds')}",
        "",
        "## Summary",
        "",
        "| # | Category | Question | Status | Rounds | Tool calls |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['id']} | {r['category']} | {md_cell(r['question'])} | {r['status']} "
                     f"| {r['rounds']} | {len(r['calls'])} |")

    for r in results:
        lines += [
            "",
            f"## {r['id']}. {r['category']}",
            "",
            f"**Question:** {r['question']}",
            "",
            f"**Check:** {r['expect']}",
            "",
            "**Answer:**",
            "",
        ]
        lines += [f"> {l}" if l else ">" for l in (r["answer"] or "(no answer)").splitlines()]
        lines += ["", "**Tool calls:**", ""]
        lines += [f"- `{c}`" for c in r["calls"]] or ["- (none)"]
        if r["errors"]:
            lines += ["", "**Errors:**", ""]
            lines += [f"- {md_cell(e)}" for e in r["errors"]]
        lines += [
            "",
            f"Status: {r['status']} · Rounds: {r['rounds']} · {r['duration_s']:.1f} s · "
            f"Log: `{r['log']}`",
            "",
            "**Verdict:** ☐ pass ☐ fail · **Notes:**",
        ]

    REPORT_DIR.mkdir(exist_ok=True)
    path = REPORT_DIR / f"{started.strftime('%Y%m%d-%H%M%S')}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m manual_tests")
    parser.add_argument("--today", default=DEFAULT_TODAY,
                        help=f"date relative questions resolve against (default {DEFAULT_TODAY})")
    parser.add_argument("--only", help="comma-separated question ids, e.g. 1,5,7")
    opts = parser.parse_args()

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    try:
        today = date.fromisoformat(opts.today)
        wanted = {int(x) for x in opts.only.split(",")} if opts.only else None
        cfg = load_config()
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    questions = [q for q in QUESTIONS if wanted is None or q["id"] in wanted]
    started = datetime.now()
    results = []
    for i, q in enumerate(questions, 1):
        log = RunLog(cfg.model)
        t0 = time.perf_counter()
        try:
            answer, status = run_agent(q["question"], cfg, log, today), "ok"
        except Exception as exc:  # record and carry on with the next question
            answer, status = f"{type(exc).__name__}: {exc}", "error"
            log.write("error", ok=False, error=answer)
        info = read_log(log.path)
        results.append({**q, **info, "answer": answer, "status": status,
                        "duration_s": time.perf_counter() - t0,
                        "log": log.path.relative_to(REPO_ROOT).as_posix()})
        print(f"[{i:02d}/{len(questions)}] {status:5} {info['rounds']} rounds  {q['question']}")

    path = write_report(results, cfg.model, today, started)
    print(f"\nReport: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
