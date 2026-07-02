"""ReleaseGate — 发布闸门

基于阈值判断评估报告是否通过发布闸门。

两级闸门:
- Smoke Gate: 快速验证, 低阈值(3.0分/80%通过率)
- Release Gate: 完整发布, 高阈值(4.0分/90%通过率)
"""

from dataclasses import dataclass, field
from backend.agent.evaluation.runner import EvalReport


@dataclass
class GateCondition:
    """单个闸门条件

    Usage:
        GateCondition(
            metric="prompt",
            operator=">=",
            threshold=3.0,
            description="Prompt评分 >= 3.0",
        )
    """

    metric: str         # 评估组件名(e.g. "prompt", "rag", "tool_call")
    operator: str       # ">=", "<=", ">", "<", "=="
    threshold: float    # 阈值
    description: str = ""


@dataclass
class GateResult:
    """闸门检查结果"""

    gate_name: str
    passed: bool
    conditions_results: list[dict] = field(default_factory=list)
    summary: str = ""

    def get_failed_conditions(self) -> list[dict]:
        """返回所有未通过的条件"""
        return [c for c in self.conditions_results if not c.get("passed", False)]


class ReleaseGate:
    """发布闸门

    定义一组GateCondition, 检查EvalReport是否满足所有条件。

    Usage:
        gate = ReleaseGate("smoke", [
            GateCondition("prompt", ">=", 3.0),
            GateCondition("tool_call", ">=", 0.8),
        ])
        result = gate.evaluate(report)
        print(f"Passed: {result.passed}")
    """

    def __init__(self, name: str, conditions: list[GateCondition]):
        self.name = name
        self.conditions = conditions

    def evaluate(self, report: EvalReport) -> GateResult:
        """评估报告是否通过闸门

        Args:
            report: 评估报告

        Returns:
            GateResult含每个条件的通过/失败详情
        """
        conditions_results = []
        all_pass = True

        for condition in self.conditions:
            actual = self._get_metric_value(report, condition.metric)
            passed = self._check_condition(actual, condition.operator, condition.threshold)

            result = {
                "metric": condition.metric,
                "operator": condition.operator,
                "threshold": condition.threshold,
                "actual": actual,
                "passed": passed,
                "description": condition.description,
            }
            conditions_results.append(result)

            if not passed:
                all_pass = False

        # 构建summary
        failed_count = sum(1 for r in conditions_results if not r["passed"])
        if all_pass:
            summary = f"通过: 所有{len(self.conditions)}个条件均满足"
        else:
            summary = f"未通过: {failed_count}/{len(self.conditions)}个条件不满足"

        return GateResult(
            gate_name=self.name,
            passed=all_pass,
            conditions_results=conditions_results,
            summary=summary,
        )

    def _get_metric_value(self, report: EvalReport, metric: str) -> float:
        """从EvalReport中提取指标值

        支持的metric路径:
        - 组件名(e.g. "prompt", "rag"): 返回该组件的avg_score
        - 组件名.pass_rate(e.g. "tool_call.pass_rate"): 返回通过率
        """
        # 处理 "component.pass_rate" 格式
        if "." in metric:
            parts = metric.split(".")
            component = parts[0]
            sub_metric = parts[1]

            comp_summary = report.summary.get(component)
            if comp_summary is None:
                return 0.0

            if sub_metric == "pass_rate":
                if comp_summary.total == 0:
                    return 0.0
                return round(comp_summary.passed / comp_summary.total, 2)
            else:
                return 0.0

        # 直接的组件名: 返回avg_score
        comp_summary = report.summary.get(metric)
        if comp_summary is not None:
            return comp_summary.avg_score

        # 全局dimension_scores
        return report.dimension_scores.get(metric, 0.0)

    @staticmethod
    def _check_condition(actual: float, operator: str, threshold: float) -> bool:
        """检查条件运算符"""
        if operator == ">=":
            return actual >= threshold
        elif operator == "<=":
            return actual <= threshold
        elif operator == ">":
            return actual > threshold
        elif operator == "<":
            return actual < threshold
        elif operator == "==":
            return actual == threshold
        else:
            return False
