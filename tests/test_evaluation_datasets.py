"""评估数据集测试 — 验证每个Worker的数据集结构和约束"""

import pytest
from backend.agent.evaluation.dataset import EvalExample, EvalDataset
from backend.agent.evaluation.datasets import (
    ALL_DATASETS,
    searcher_dataset,
    profiler_dataset,
    scheduler_dataset,
    goal_decomposer_dataset,
    coach_dataset,
    orchestrator_dataset,
)


class TestEvalExample:
    """EvalExample 数据结构"""

    def test_valid_example(self):
        ex = EvalExample(
            id="test-1",
            name="test",
            description="test desc",
            worker="searcher",
            eval_type="prompt",
            tags=["smoke"],
        )
        assert ex.id == "test-1"
        assert ex.tags == ["smoke"]

    def test_invalid_eval_type(self):
        with pytest.raises(ValueError):
            EvalExample(
                id="x", name="x", description="x",
                worker="x", eval_type="invalid_type",
            )

    def test_default_tags(self):
        ex = EvalExample(
            id="x", name="x", description="x",
            worker="x", eval_type="prompt",
        )
        assert ex.tags == []


class TestEvalDataset:
    """EvalDataset 过滤方法"""

    @pytest.fixture
    def ds(self):
        return EvalDataset(
            name="test-ds",
            description="test",
            examples=[
                EvalExample(id="1", name="a", description="d", worker="searcher", eval_type="prompt", tags=["smoke"]),
                EvalExample(id="2", name="b", description="d", worker="searcher", eval_type="tool_call", tags=["critical"]),
                EvalExample(id="3", name="c", description="d", worker="profiler", eval_type="prompt", tags=["smoke"]),
            ],
        )

    def test_filter_by_worker(self, ds):
        f = ds.filter_by_worker("searcher")
        assert len(f) == 2
        assert all(e.worker == "searcher" for e in f.examples)

    def test_filter_by_type(self, ds):
        f = ds.filter_by_type("prompt")
        assert len(f) == 2
        assert all(e.eval_type == "prompt" for e in f.examples)

    def test_filter_by_tags(self, ds):
        f = ds.filter_by_tags(["smoke"])
        assert len(f) == 2

    def test_filter_by_tags_multiple(self, ds):
        f = ds.filter_by_tags(["critical"])
        assert len(f) == 1

    def test_get_workers(self, ds):
        workers = ds.get_workers()
        assert "searcher" in workers
        assert "profiler" in workers

    def test_get_types(self, ds):
        types = ds.get_types()
        assert "prompt" in types
        assert "tool_call" in types


class TestDatasetsMinimumExamples:
    """每个Worker的数据集至少有5个examples"""

    def test_searcher_min_examples(self):
        assert len(searcher_dataset) >= 5

    def test_profiler_min_examples(self):
        assert len(profiler_dataset) >= 5

    def test_scheduler_min_examples(self):
        assert len(scheduler_dataset) >= 5

    def test_goal_decomposer_min_examples(self):
        assert len(goal_decomposer_dataset) >= 5

    def test_coach_min_examples(self):
        assert len(coach_dataset) >= 5

    def test_orchestrator_min_examples(self):
        assert len(orchestrator_dataset) >= 5


class TestDatasetsCoverage:
    """数据集覆盖评估维度"""

    def test_searcher_has_prompt_examples(self):
        prompt_examples = searcher_dataset.filter_by_type("prompt")
        assert len(prompt_examples) >= 1

    def test_searcher_has_tool_call_examples(self):
        tc_examples = searcher_dataset.filter_by_type("tool_call")
        assert len(tc_examples) >= 1

    def test_searcher_has_rag_examples(self):
        rag_examples = searcher_dataset.filter_by_type("rag")
        assert len(rag_examples) >= 1

    def test_coach_has_reasoning_examples(self):
        reasoning = coach_dataset.filter_by_type("reasoning")
        assert len(reasoning) >= 5  # CBT六场景

    def test_orchestrator_has_trajectory_examples(self):
        traj = orchestrator_dataset.filter_by_type("trajectory")
        assert len(traj) >= 5


class TestDatasetIdsUnique:
    """所有数据集中的example ID必须唯一"""

    def test_all_ids_unique(self):
        all_ids = []
        for ds in ALL_DATASETS:
            for ex in ds.examples:
                all_ids.append(ex.id)
        assert len(all_ids) == len(set(all_ids)), f"Duplicate IDs found: {[x for x in all_ids if all_ids.count(x) > 1]}"
