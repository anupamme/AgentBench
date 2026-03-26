class ReportFormatter:
    def __init__(self, data: list):
        self._data = data

    def format(self, title: str = "Report") -> dict:
        return {"title": title, "rows": self._data}

    def format_filtered(self, key: str, value) -> dict:
        filtered = [r for r in self._data if r.get(key) == value]
        return {"title": "Filtered", "rows": filtered}
