from pathlib import Path
import json
from .metrics import MetricRecord, to_dict

def write_report(records: list[MetricRecord], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps([to_dict(r) for r in records], indent=2), encoding="utf8")
