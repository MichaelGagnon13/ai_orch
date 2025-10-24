import json, pathlib

PLAN = pathlib.Path("state/plan.json")
LOGS = pathlib.Path("rag/logs/tasks.jsonl")
OUT  = pathlib.Path("rag/summaries/summary.md")

def load_plan():
    return json.loads(PLAN.read_text()) if PLAN.exists() else {}

def load_logs(n=50):
    if not LOGS.exists(): return []
    lines = LOGS.read_text().splitlines()[-n:]
    return [json.loads(l) for l in lines if l.strip()]

def render(plan, logs):
    def line(k, d, default=""):
        v = d.get(k, default)
        return v if isinstance(v, str) else str(v)
    rows = []
    for key, item in plan.items():
        if isinstance(item, dict) and item.get("id","").startswith("TASK-"):
            rows.append((item["id"], item.get("title",""), item.get("status",""), item.get("criteria","")))
    rows.sort()
    md = []
    md.append("# Résumé AgentScope\n")
    md.append("## Tâches\n")
    md.append("| id | titre | statut | critères |")
    md.append("|---|---|---|---|")
    for tid, title, status, crit in rows:
        md.append(f"| {tid} | {title} | {status} | {crit} |")
    md.append("\n## Derniers événements\n")
    for e in logs:
        md.append(f"- {e.get('ts')} · {e.get('event')} · {e.get('task_id')} → {e.get('status')} {e.get('note','')}".rstrip())
    return "\n".join(md) + "\n"

def main():
    plan = load_plan()
    logs = load_logs(50)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(plan, logs), encoding="utf-8")
    print(f"OK: écrit {OUT}")

if __name__ == "__main__":
    main()
