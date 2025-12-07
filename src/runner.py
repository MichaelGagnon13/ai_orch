import json
import pathlib
import re
import subprocess
import time

from src.logger import log_task
from src.plan import load_plan, next_open_task

PLAN_PATH = pathlib.Path("state/plan.json")


def extract_k(criteria: str) -> str | None:
    if not criteria:
        return None
    m = re.search(r"-k\s+([\"']?)(.+?)\1(\s|$)", criteria)
    return m.group(2) if m else None


def mark(plan, tid, status):
    # simple dict-level update
    if tid in plan:
        plan[tid]["status"] = status
        plan[tid][f"{status}_at"] = int(time.time())


def main():
    plan = load_plan(PLAN_PATH.as_posix())
    t = next_open_task(plan)
    if not t:
        print("NEXT: NONE")
        return
    tid = t["id"]
    crit = t.get("criteria", "")
    k = extract_k(crit)
    cmd = ["pytest", "-q"] + (["-k", k] if k else [])
    print(f"[runner] {tid} -> {' '.join(cmd)}")
    rc = subprocess.run(cmd).returncode
    status = "done" if rc == 0 else "blocked"
    mark(plan, tid, status)
    PLAN_PATH.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    log_task("status", tid, status, {"rc": rc, "k": k})
    print(f"[runner] {tid} -> {status} (rc={rc})")


if __name__ == "__main__":
    main()
