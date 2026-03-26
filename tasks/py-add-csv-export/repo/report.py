import json


class Report:
    def __init__(self, title: str, records: list[dict]):
        self.title = title
        self.records = records

    def to_json(self) -> str:
        """Export the report as a JSON string."""
        return json.dumps({"title": self.title, "records": self.records}, indent=2)

    def row_count(self) -> int:
        """Return the number of records."""
        return len(self.records)
