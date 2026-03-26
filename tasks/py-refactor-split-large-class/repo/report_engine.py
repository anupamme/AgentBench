import json
import csv
import io


class ReportEngine:
    def __init__(self):
        self._raw_data = []
        self._formatted = []

    # --- Data Loading ---
    def load_from_list(self, records: list):
        self._raw_data = records

    def load_from_json(self, json_str: str):
        self._raw_data = json.loads(json_str)

    # --- Formatting ---
    def format(self, title: str = "Report"):
        self._formatted = [{"title": title, "rows": self._raw_data}]

    def format_filtered(self, key: str, value):
        filtered = [r for r in self._raw_data if r.get(key) == value]
        self._formatted = [{"title": "Filtered", "rows": filtered}]

    # --- Export ---
    def to_json(self) -> str:
        return json.dumps(self._formatted, indent=2)

    def to_csv(self) -> str:
        if not self._formatted or not self._formatted[0]["rows"]:
            return ""
        rows = self._formatted[0]["rows"]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
        return buf.getvalue()

    def row_count(self) -> int:
        if not self._formatted:
            return 0
        return len(self._formatted[0]["rows"])
