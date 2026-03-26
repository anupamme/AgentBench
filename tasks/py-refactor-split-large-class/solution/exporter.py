import csv
import io
import json


class ReportExporter:
    def __init__(self, formatted: dict):
        self._formatted = formatted

    def to_json(self) -> str:
        return json.dumps(self._formatted, indent=2)

    def to_csv(self) -> str:
        rows = self._formatted.get("rows", [])
        if not rows:
            return ""
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
        return buf.getvalue()

    def row_count(self) -> int:
        return len(self._formatted.get("rows", []))
