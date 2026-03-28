from exporter import ReportExporter
from formatter import ReportFormatter
from loader import DataLoader

RECORDS = [{"name": "Alice", "score": 90}, {"name": "Bob", "score": 70}]


def test_loader_from_list():
    dl = DataLoader()
    dl.load_from_list(RECORDS)
    assert dl.data == RECORDS


def test_loader_from_json():
    import json

    dl = DataLoader()
    dl.load_from_json(json.dumps(RECORDS))
    assert len(dl.data) == 2


def test_formatter_basic():
    dl = DataLoader()
    dl.load_from_list(RECORDS)
    fmt = ReportFormatter(dl.data)
    result = fmt.format(title="Test")
    assert result["title"] == "Test"
    assert len(result["rows"]) == 2


def test_formatter_filtered():
    dl = DataLoader()
    dl.load_from_list(RECORDS)
    fmt = ReportFormatter(dl.data)
    result = fmt.format_filtered("name", "Alice")
    assert len(result["rows"]) == 1


def test_exporter_json():
    ex = ReportExporter({"title": "T", "rows": RECORDS})
    j = ex.to_json()
    import json

    data = json.loads(j)
    assert data["title"] == "T"


def test_exporter_csv():
    ex = ReportExporter({"title": "T", "rows": RECORDS})
    csv_str = ex.to_csv()
    lines = csv_str.strip().splitlines()
    assert len(lines) == 3  # header + 2 rows


def test_exporter_row_count():
    ex = ReportExporter({"title": "T", "rows": RECORDS})
    assert ex.row_count() == 2
