"""评估数据集 — 各Worker的黄金测试集

每个Worker至少5个EvalExample, 覆盖prompt/tool_call/reasoning/rag/trajectory维度。
"""

from backend.agent.evaluation.datasets.searcher import searcher_dataset
from backend.agent.evaluation.datasets.profiler import profiler_dataset
from backend.agent.evaluation.datasets.scheduler import scheduler_dataset
from backend.agent.evaluation.datasets.goal_decomposer import goal_decomposer_dataset
from backend.agent.evaluation.datasets.coach import coach_dataset
from backend.agent.evaluation.datasets.orchestrator import orchestrator_dataset

# 所有数据集的汇总列表
ALL_DATASETS: list = [
    searcher_dataset,
    profiler_dataset,
    scheduler_dataset,
    goal_decomposer_dataset,
    coach_dataset,
    orchestrator_dataset,
]

# 按Worker名称索引
DATASETS_BY_WORKER: dict[str, list] = {}
for ds in ALL_DATASETS:
    for worker in ds.get_workers():
        if worker not in DATASETS_BY_WORKER:
            DATASETS_BY_WORKER[worker] = []
        DATASETS_BY_WORKER[worker].append(ds)

__all__ = [
    "ALL_DATASETS",
    "DATASETS_BY_WORKER",
    "searcher_dataset",
    "profiler_dataset",
    "scheduler_dataset",
    "goal_decomposer_dataset",
    "coach_dataset",
    "orchestrator_dataset",
]
