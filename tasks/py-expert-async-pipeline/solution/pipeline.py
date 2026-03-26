import asyncio


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


class AsyncPipeline:
    def __init__(self, stages):
        self.stages = stages

    async def _process_item(self, item):
        value = item
        for stage in self.stages:
            value = await stage(value)
        return value

    async def run(self, items):
        return list(await asyncio.gather(*[self._process_item(item) for item in items]))
