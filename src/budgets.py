import json, pathlib, time

def load_budgets(path="state/budgets.json"):
    p = pathlib.Path(path)
    data = json.loads(p.read_text())
    profiles = data.get("profiles", {})
    active = data.get("active_profile", "small")
    cfg = profiles.get(active, {})
    return {
        "meta": {"updated_at": data.get("updated_at"), "active_profile": active},
        "per_step": cfg.get("per_step", {}),
        "per_task": cfg.get("per_task", {}),
        "cost_limits": cfg.get("cost_limits", {}),
        "policy": data.get("policy", {})
    }

if __name__ == "__main__":
    b = load_budgets()
    print("active_profile=", b["meta"]["active_profile"])
    print("per_step=", b["per_step"])
    print("per_task=", b["per_task"])
    print("policy=", b["policy"])
