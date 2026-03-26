from stage import Stage


class FilterStage(Stage):
    def __init__(self, min_value):
        self.min_value = min_value

    def process(self, data: list) -> list:
        return [x for x in data if x >= self.min_value]
