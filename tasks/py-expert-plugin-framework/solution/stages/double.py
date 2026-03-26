from stage import Stage


class DoubleStage(Stage):
    def process(self, data: list) -> list:
        return [x * 2 for x in data]
