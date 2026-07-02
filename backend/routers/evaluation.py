"""Agent评估API — 触发评估运行、查询评估结果"""

import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.database import SessionLocal
from backend.models import AgentEvaluationRun, AgentEvaluationResult

router = APIRouter(prefix="/api/v1/agent/evaluation", tags=["agent-evaluation"])


# ── Schema ──

class EvalRunRequest(BaseModel):
    name: str = "manual"
    components: list[str] = ["prompt", "tool_call", "reasoning", "rag", "trajectory"]
    workers: list[str] = []
    tags: list[str] = []
    gates: list[str] = ["smoke"]


# ── Helpers ──

def _ok(data):
    from fastapi.responses import JSONResponse
    return JSONResponse({"code": 0, "message": "success", "data": data})


def _get_llm():
    """获取当前LLM插件实例"""
    try:
        from backend.routers.agent import get_harness
        harness = get_harness()
        if harness:
            return harness.registry.get("llm")
    except Exception:
        pass
    return None


# ── Endpoints ──

@router.post("/run")
async def run_evaluation(req: EvalRunRequest):
    """触发一次评估运行

    同步执行所有评估组件, 返回完整的EvalReport。
    结果持久化到agent_evaluation_runs和agent_evaluation_results表。
    """
    llm = _get_llm()
    if llm is None:
        return _ok({
            "passed": False,
            "error": "LLM未初始化, 无法运行评估",
        })

    from backend.agent.evaluation.runner import EvalRunner, EvalConfig
    from backend.agent.evaluation.default_gates import GATES_BY_NAME

    config = EvalConfig(
        name=req.name,
        components=req.components,
        workers=req.workers,
        tags=req.tags,
    )

    runner = EvalRunner(llm, config)
    report = await runner.run_all()

    # 检查闸门
    for gate_name in req.gates:
        gate = GATES_BY_NAME.get(gate_name)
        if gate:
            gate_result = gate.evaluate(report)
            report.gates_results.append(gate_result)

    # 如果所有闸门都不通过, report.passed = False
    if report.gates_results and not all(g.passed for g in report.gates_results):
        report.passed = False

    # 持久化结果
    try:
        db = SessionLocal()
        try:
            run_record = AgentEvaluationRun(
                eval_name=req.name,
                config_json=json.dumps({
                    "components": req.components,
                    "workers": req.workers,
                    "tags": req.tags,
                    "gates": req.gates,
                }, ensure_ascii=False),
                passed=report.passed,
                score=sum(report.dimension_scores.values()) / max(len(report.dimension_scores), 1),
                metrics_json=json.dumps(report.dimension_scores, ensure_ascii=False),
                summary_json=json.dumps({
                    k: {
                        "total": v.total,
                        "passed": v.passed,
                        "failed": v.failed,
                        "avg_score": v.avg_score,
                    }
                    for k, v in report.summary.items()
                }, ensure_ascii=False),
                failure_reason="" if report.passed else "部分闸门未通过",
                duration_ms=report.total_duration_ms,
            )
            db.add(run_record)
            db.commit()
            db.refresh(run_record)

            # 存储明细
            for score in report.results:
                db.add(AgentEvaluationResult(
                    run_id=run_record.id,
                    example_id=score.rubric_name,
                    worker=score.rubric_name,
                    eval_type=score.rubric_name,
                    score=score.overall_score,
                    passed=score.overall_score >= 3.0,
                    dimension_scores_json=json.dumps(score.dimension_scores, ensure_ascii=False),
                    reasoning=score.reasoning[:500],
                ))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        # DB持久化失败不影响API返回
        pass

    return _ok(report.to_dict())


@router.get("/runs")
async def list_evaluation_runs(
    limit: int = Query(10, ge=1, le=100),
    passed: str = Query("", description="true/false/空=全部"),
    name: str = Query("", description="按eval_name过滤"),
):
    """获取评估运行列表, 按时间倒序"""
    db = SessionLocal()
    try:
        q = db.query(AgentEvaluationRun)
        if passed == "true":
            q = q.filter(AgentEvaluationRun.passed == True)
        elif passed == "false":
            q = q.filter(AgentEvaluationRun.passed == False)
        if name:
            q = q.filter(AgentEvaluationRun.eval_name == name)

        runs = q.order_by(AgentEvaluationRun.created_at.desc()).limit(limit).all()

        return _ok([{
            "id": r.id,
            "eval_name": r.eval_name,
            "passed": r.passed,
            "score": r.score,
            "duration_ms": r.duration_ms,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        } for r in runs])
    finally:
        db.close()


@router.get("/runs/{run_id}")
async def get_evaluation_run_detail(run_id: int):
    """获取单次评估运行的完整详情(含各用例结果)"""
    db = SessionLocal()
    try:
        run = db.query(AgentEvaluationRun).filter(AgentEvaluationRun.id == run_id).first()
        if not run:
            raise HTTPException(404, "评估运行不存在")

        results = db.query(AgentEvaluationResult).filter(
            AgentEvaluationResult.run_id == run_id
        ).all()

        return _ok({
            "run": {
                "id": run.id,
                "eval_name": run.eval_name,
                "passed": run.passed,
                "score": run.score,
                "metrics": json.loads(run.metrics_json or "{}"),
                "summary": json.loads(run.summary_json or "{}"),
                "failure_reason": run.failure_reason,
                "duration_ms": run.duration_ms,
                "created_at": run.created_at.isoformat() if run.created_at else "",
            },
            "results": [{
                "id": r.id,
                "example_id": r.example_id,
                "worker": r.worker,
                "eval_type": r.eval_type,
                "score": r.score,
                "passed": r.passed,
                "dimension_scores": json.loads(r.dimension_scores_json or "{}"),
                "reasoning": r.reasoning,
            } for r in results],
        })
    finally:
        db.close()


@router.get("/datasets")
async def list_datasets(worker: str = Query("", description="按Worker过滤")):
    """获取可用评估数据集列表"""
    from backend.agent.evaluation.datasets import ALL_DATASETS

    datasets = []
    for ds in ALL_DATASETS:
        if worker and worker not in ds.get_workers():
            continue
        datasets.append({
            "name": ds.name,
            "description": ds.description,
            "example_count": len(ds),
            "workers": ds.get_workers(),
        })
    return _ok(datasets)


@router.get("/summary")
async def evaluation_summary():
    """获取评估仪表盘摘要"""
    db = SessionLocal()
    try:
        last_run = db.query(AgentEvaluationRun).order_by(
            AgentEvaluationRun.created_at.desc()
        ).first()

        recent_runs = db.query(AgentEvaluationRun).order_by(
            AgentEvaluationRun.created_at.desc()
        ).limit(10).all()

        return _ok({
            "last_run": {
                "id": last_run.id,
                "eval_name": last_run.eval_name,
                "passed": last_run.passed,
                "score": last_run.score,
                "created_at": last_run.created_at.isoformat() if last_run.created_at else "",
            } if last_run else None,
            "recent": [{
                "date": r.created_at.date().isoformat() if r.created_at else "",
                "score": r.score,
                "passed": r.passed,
            } for r in recent_runs],
        })
    finally:
        db.close()
