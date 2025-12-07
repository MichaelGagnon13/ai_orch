import json
import pathlib
import time


def _ts():
    return int(time.time())


def append_jsonl(path, record: dict):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _ts(), **record}, ensure_ascii=False) + "\n")


def log_task(event: str, task_id: str, status: str, extra: dict | None = None):
    append_jsonl(
        "rag/logs/tasks.jsonl",
        {"event": event, "task_id": task_id, "status": status, **(extra or {})},
    )


if __name__ == "__main__":
    log_task("test_write", "TASK-1", "done", {"note": "smoke"})
    print("OK: wrote rag/logs/tasks.jsonl")
