"""优先级引擎工厂"""

from backend.agent.plugins.priority_engine.base import PriorityEngineBase
from backend.agent.plugins.priority_engine.weighted_scorer import WeightedScorer


class PriorityFactory:
    """优先级引擎工厂"""

    _engines = {
        "weighted": WeightedScorer,
    }

    @classmethod
    def create(cls, provider: str = "weighted") -> PriorityEngineBase:
        engine_class = cls._engines.get(provider)
        if engine_class is None:
            raise ValueError(
                f"Unknown priority engine '{provider}'. "
                f"Available: {list(cls._engines.keys())}"
            )
        return engine_class()

    @classmethod
    def register(cls, name: str, engine_class: type[PriorityEngineBase]) -> None:
        if not issubclass(engine_class, PriorityEngineBase):
            raise TypeError(f"{engine_class} must be a subclass of PriorityEngineBase")
        cls._engines[name] = engine_class
