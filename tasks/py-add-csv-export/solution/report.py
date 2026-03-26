import csv
import io
import json


class Report:
    def __init__(self, title: str, records: list[dict]):
        self.title = title
        self.records = records

    def to_json(self) -> str:
        """Export the report as a JSON string."""
        return json.dumps({"title": self.title, "records": self.records}, indent=2)

    def to_csv(self) -> str:
        """Export the report as a CSV string."""
        if not self.records:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.records[0].keys())
        writer.writeheader()
        writer.writerows(self.records)
        return output.getvalue()

    def row_count(self) -> int:
        """Return the number of records."""
        return len(self.records)
