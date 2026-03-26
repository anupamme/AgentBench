class Pipeline:
    def __init__(self, stages):
        self.stages = stages

    def run(self, items):
        results = []
        for item in items:
            value = item
            for stage in self.stages:
                value = stage(value)
            results.append(value)
        return results
