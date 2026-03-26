import json


class DataLoader:
    def __init__(self):
        self.data = []

    def load_from_list(self, records: list):
        self.data = records

    def load_from_json(self, json_str: str):
        self.data = json.loads(json_str)
