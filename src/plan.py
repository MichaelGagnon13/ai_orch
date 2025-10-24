import json, pathlib

def load_plan(path="state/plan.json"):
    p = pathlib.Path(path)
    return json.loads(p.read_text())

def iter_tasks(node):
    if isinstance(node, dict):
        if node.get("id","").startswith("TASK-"):
            yield node
        for v in node.values():
            yield from iter_tasks(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_tasks(v)

def next_open_task(plan):
    for t in iter_tasks(plan):
        if t.get("status") not in ("done","blocked"):
            return t
    return None

if __name__ == "__main__":
    plan = load_plan()
    t = next_open_task(plan)
    print("NEXT:", t["id"] if t else "NONE")
