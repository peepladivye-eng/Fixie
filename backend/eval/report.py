import json
from pathlib import Path

report = json.loads((Path(__file__).parent / "eval.json").read_text(encoding="utf-8"))
print("mode       resolved rounds cost_usd seconds")
for name in ("baseline", "branching"):
    row = report[name]
    print(f"{name:10} {row['resolved']:8} {row['rounds']:6} {row['cost_usd']:8.3f} {row['seconds']:7.3f}")
