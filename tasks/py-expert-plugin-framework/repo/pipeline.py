class Pipeline:
    def run(self, data: list) -> list:
        result = [x * 2 for x in data]
        result = [x for x in result if x > 4]
        return result
