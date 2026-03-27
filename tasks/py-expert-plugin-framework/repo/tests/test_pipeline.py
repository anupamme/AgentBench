from stage import Stage
from stages.double import DoubleStage
from stages.filter import FilterStage
from pipeline import Pipeline


def test_stage_is_abstract():
    import inspect
    assert inspect.isabstract(Stage)


def test_double_stage():
    s = DoubleStage()
    assert s.process([1, 2, 3]) == [2, 4, 6]


def test_filter_stage():
    s = FilterStage(min_value=4)
    assert s.process([2, 4, 6, 8]) == [4, 6, 8]


def test_pipeline_with_stages():
    p = Pipeline([DoubleStage(), FilterStage(min_value=4)])
    assert p.run([1, 2, 3, 4]) == [4, 6, 8]


def test_pipeline_empty_stages():
    p = Pipeline([])
    assert p.run([1, 2, 3]) == [1, 2, 3]
