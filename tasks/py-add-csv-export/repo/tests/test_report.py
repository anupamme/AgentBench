from report import Report

RECORDS = [
    {"name": "Alice", "score": 95, "grade": "A"},
    {"name": "Bob", "score": 82, "grade": "B"},
]


def test_to_json():
    r = Report("Test", RECORDS)
    import json

    data = json.loads(r.to_json())
    assert data["title"] == "Test"
    assert len(data["records"]) == 2


def test_row_count():
    r = Report("Test", RECORDS)
    assert r.row_count() == 2


def test_to_csv_headers():
    r = Report("Test", RECORDS)
    csv = r.to_csv()
    first_line = csv.strip().splitlines()[0]
    assert "name" in first_line
    assert "score" in first_line
    assert "grade" in first_line


def test_to_csv_rows():
    r = Report("Test", RECORDS)
    lines = r.to_csv().strip().splitlines()
    assert len(lines) == 3  # header + 2 data rows
    assert "Alice" in lines[1]
    assert "Bob" in lines[2]


def test_to_csv_empty():
    r = Report("Empty", [])
    lines = r.to_csv().strip().splitlines()
    assert len(lines) == 0
