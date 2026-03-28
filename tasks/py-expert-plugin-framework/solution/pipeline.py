class Pipeline:
    def __init__(self, stages: list):
        self.stages = stages

    def run(self, data: list) -> list:
        result = data
        for stage in self.stages:
            result = stage.process(result)
        return result
