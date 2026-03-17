"""
Celery evaluation task - orchestrates the evaluation engine.
Multi-model parallel execution with thread pool.
"""
import json
import asyncio
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from celery import Task
from app.core.celery_app import celery_app
from app.core.config import settings


class CeleryEvaluationTask(Task):
    abstract = True
    _db_session = None

    def get_sync_session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
        engine = create_engine(sync_url)
        Session = sessionmaker(bind=engine)
        return Session()

    def get_redis(self):
        import redis
        return redis.from_url(settings.REDIS_URL)


@celery_app.task(bind=True, base=CeleryEvaluationTask, name="app.services.evaluation.run_evaluation_task")
def run_evaluation_task(self, task_id: int):
    """Main evaluation orchestrator running in Celery worker.
    Multiple models are evaluated in parallel using a thread pool.
    """
    from app.db.models import EvaluationTask, EvaluationResult, ModelConfig, Dataset, ModelEloScore
    from app.core.security import decrypt_api_key

    session = self.get_sync_session()
    redis_client = self.get_redis()

    def publish_progress(data: dict):
        try:
            redis_client.publish(f"eval_progress:{task_id}", json.dumps(data))
        except Exception:
            pass

    try:
        task = session.get(EvaluationTask, task_id)
        if not task:
            return {"error": "Task not found"}

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        session.commit()
        publish_progress({"status": "running", "progress": 0, "message": "正在准备评测环境..."})

        # Load models
        publish_progress({"status": "running", "progress": 0, "message": "正在加载模型配置..."})
        model_configs = []
        for mid in task.model_ids:
            mc = session.get(ModelConfig, mid)
            if mc:
                api_key = decrypt_api_key(mc.api_key_encrypted) if mc.api_key_encrypted else None
                model_configs.append({
                    "id": mc.id,
                    "name": mc.name,
                    "provider": mc.provider,
                    "api_key": api_key,
                    "base_url": mc.base_url,
                    "model_name": mc.model_name,
                    "params": mc.params or {},
                })

        # Load dataset
        samples = []
        if task.dataset_id:
            publish_progress({"status": "running", "progress": 0, "message": "正在加载数据集..."})
            dataset = session.get(Dataset, task.dataset_id)
            if dataset and dataset.file_path:
                from app.services.storage import StorageService
                storage = StorageService()
                loop = asyncio.new_event_loop()
                content = loop.run_until_complete(storage.download_bytes(dataset.file_path))
                loop.close()
                for line in content.decode("utf-8").strip().split("\n"):
                    if line.strip():
                        samples.append(json.loads(line))

        # Validate & fill defaults for evaluator_config
        from app.schemas.evaluation import EvaluatorConfig as EvaluatorConfigSchema
        try:
            validated_config = EvaluatorConfigSchema(**(task.evaluator_config or {}))
            config = validated_config.model_dump()
        except Exception:
            config = task.evaluator_config or {}

        # Load benchmark samples when no dataset is provided
        if not samples and config.get("benchmarks"):
            import sys as _sys, os as _os
            eval_engine_path = _os.environ.get("EVAL_ENGINE_PATH", "/eval_engine")
            if not _os.path.isdir(eval_engine_path):
                eval_engine_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "..", "eval_engine")
            _sys.path.insert(0, eval_engine_path)
            from evaluators.benchmark import BenchmarkEvaluator
            bm_max = config.get("max_samples")
            for benchmark_id in config["benchmarks"]:
                publish_progress({"status": "running", "progress": 0, "message": f"正在加载基准测试数据: {benchmark_id}..."})
                bm_samples = BenchmarkEvaluator.load_dataset(benchmark_id, max_samples=bm_max)
                for s in bm_samples:
                    s["_benchmark_id"] = benchmark_id
                    samples.append(s)

        # Load domain prompts if domain_eval enabled
        if config.get("domain_eval"):
            from app.db.models import PromptTemplate
            gen_prompts = []
            for pid in config.get("generation_prompt_ids", []):
                pt = session.get(PromptTemplate, pid)
                if pt:
                    gen_prompts.append(pt.content)
            eval_prompts = []
            for pid in config.get("evaluation_prompt_ids", []):
                pt = session.get(PromptTemplate, pid)
                if pt:
                    eval_prompts.append(pt.content)
            config["generation_prompts"] = gen_prompts
            config["evaluation_prompts"] = eval_prompts

        # --- Inject builtin samples when no dataset/benchmark is provided ---
        if not samples and not config.get("benchmarks"):
            import sys as _sys, os as _os
            eval_engine_path = _os.environ.get("EVAL_ENGINE_PATH", "/eval_engine")
            if not _os.path.isdir(eval_engine_path):
                eval_engine_path = _os.path.join(
                    _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
                    "..", "eval_engine",
                )
            _sys.path.insert(0, eval_engine_path)

            builtin_map = [
                ("instruction_following", "evaluators.instruction_following", "InstructionFollowingEvaluator", "get_builtin_samples"),
                ("cot_reasoning", "evaluators.cot_reasoning", "ChainOfThoughtEvaluator", "get_builtin_samples"),
                ("structured_output", "evaluators.structured_output", "StructuredOutputEvaluator", "get_builtin_samples"),
                ("multilingual", "evaluators.multilingual", "MultilingualEvaluator", "get_builtin_samples"),
                ("tool_calling", "evaluators.tool_calling", "ToolCallingEvaluator", "get_builtin_samples"),
                ("long_context", "evaluators.long_context", "LongContextEvaluator", "get_builtin_needles"),
                ("multimodal", "evaluators.multimodal", "MultimodalEvaluator", "get_builtin_samples"),
            ]

            for config_key, module_path, class_name, method_name in builtin_map:
                if config.get(config_key):
                    try:
                        mod = __import__(module_path, fromlist=[class_name])
                        evaluator_cls = getattr(mod, class_name)
                        evaluator = evaluator_cls()
                        builtin = getattr(evaluator, method_name)()
                        for s in builtin:
                            s["_evaluator_type"] = config_key
                            samples.append(s)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()

            if samples:
                publish_progress({
                    "status": "running", "progress": 0,
                    "message": f"使用内置评测样本 ({len(samples)} 条)...",
                })

        max_samples = config.get("max_samples")
        if max_samples:
            samples = samples[:max_samples]

        total = len(samples) * len(model_configs)
        if total == 0:
            err_msg = "没有可评测的样本"
            if not model_configs:
                err_msg = "没有有效的模型配置"
            elif not samples:
                if config.get("domain_eval") and not task.dataset_id:
                    err_msg = "垂直领域评测需要选择数据集来提供输入样本"
                elif not config.get("benchmarks"):
                    err_msg = "未选择数据集或基准测试，没有可评测的样本。请上传数据集、选择基准测试，或启用扩展评测维度（如指令遵循、思维链等）"
            task.status = "failed"
            task.progress = 0
            task.error_message = err_msg
            task.completed_at = datetime.now(timezone.utc)
            task.results_summary = {"by_model": {}, "message": err_msg}
            session.commit()
            publish_progress({"status": "failed", "progress": 0, "message": err_msg})
            return task.results_summary
        task.total_samples = total
        task.processed_samples = 0
        task.progress = 0
        session.commit()

        # Import evaluation engine
        publish_progress({"status": "running", "progress": 0, "message": f"正在初始化评测引擎 ({len(samples)} 个样本, {len(model_configs)} 个模型)..."})
        import sys, os
        eval_engine_path = os.environ.get("EVAL_ENGINE_PATH", "/eval_engine")
        if not os.path.isdir(eval_engine_path):
            eval_engine_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "eval_engine")
        sys.path.insert(0, eval_engine_path)
        from engine import EvaluationEngine

        max_retries_per_sample = task.max_retries or 3

        # --- Shared progress state (thread-safe) ---
        progress_lock = threading.Lock()
        model_progress = {str(mc["id"]): 0 for mc in model_configs}
        processed_total = [0]  # mutable container for thread access

        def make_progress_payload(message: str):
            pct = int(processed_total[0] / total * 100) if total > 0 else 0
            return {
                "status": "running",
                "progress": max(pct, 1) if processed_total[0] > 0 else 0,
                "processed": processed_total[0],
                "total": total,
                "per_model_progress": {
                    mid: {
                        "processed": cnt,
                        "total": len(samples),
                        "is_processing": cnt < len(samples),
                        "model_name": next((mc["name"] for mc in model_configs if str(mc["id"]) == mid), mid),
                    }
                    for mid, cnt in model_progress.items()
                },
                "message": message,
            }

        # Publish initial progress
        publish_progress(make_progress_payload(
            f"正在并行评测 {len(model_configs)} 个模型，每个模型 {len(samples)} 个样本"
        ))

        # --- Per-model worker function ---
        def evaluate_model(model_cfg: dict):
            """Evaluate all samples for a single model. Runs in a thread."""
            # Each thread gets its own DB session and engine instance
            from sqlalchemy import create_engine, text as sa_text
            from sqlalchemy.orm import sessionmaker
            sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
            thread_engine_db = create_engine(sync_url)
            ThreadSession = sessionmaker(bind=thread_engine_db)
            thread_session = ThreadSession()

            # Each thread gets its own EvaluationEngine to avoid state conflicts
            thread_eval_engine = EvaluationEngine(config)

            mid = str(model_cfg["id"])
            model_results = []
            import time as _time

            try:
                for i, sample in enumerate(samples):
                    # Publish "processing" message BEFORE the sample starts
                    publish_progress(make_progress_payload(
                        f"{model_cfg['name']}: 正在处理样本..."
                    ))

                    last_error = None
                    for attempt in range(max_retries_per_sample):
                        try:
                            result = thread_eval_engine.evaluate_sample(model_cfg, sample, i)
                            model_results.append(result)

                            raw_input = sample.get("input") or sample.get("question") or sample.get("prompt") or sample.get("instruction") or sample.get("problem") or sample.get("user_request", "")
                            # For multilingual/special samples, use input_display from evaluator result or prompts dict
                            if not raw_input and result.get("input_display"):
                                raw_input = result["input_display"]
                            elif not raw_input and sample.get("prompts"):
                                raw_input = "; ".join(f"[{k}] {v}" for k, v in sample["prompts"].items())
                            raw_ref = sample.get("output") or sample.get("answer") or sample.get("reference") or sample.get("expected_tool", "")
                            input_str = json.dumps(raw_input, ensure_ascii=False) if isinstance(raw_input, (list, dict)) else str(raw_input)
                            ref_str = json.dumps(raw_ref, ensure_ascii=False) if isinstance(raw_ref, (list, dict)) else str(raw_ref)

                            db_result = EvaluationResult(
                                task_id=task_id,
                                sample_index=i,
                                model_id=model_cfg["id"],
                                input_text=input_str,
                                output_text=str(result.get("output", "")),
                                reference_text=ref_str,
                                scores=result.get("scores", {}),
                                result_metadata=result.get("metadata", {}),
                                latency_ms=result.get("latency_ms"),
                                prompt_tokens=result.get("prompt_tokens"),
                                completion_tokens=result.get("completion_tokens"),
                            )
                            thread_session.add(db_result)
                            thread_session.commit()
                            last_error = None
                            break
                        except Exception as e:
                            last_error = e
                            thread_session.rollback()
                            if attempt < max_retries_per_sample - 1:
                                _time.sleep(2 ** attempt)

                    if last_error is not None:
                        raw_input = sample.get("input") or sample.get("question") or sample.get("prompt", "")
                        input_str = json.dumps(raw_input, ensure_ascii=False) if isinstance(raw_input, (list, dict)) else str(raw_input)
                        thread_session.add(EvaluationResult(
                            task_id=task_id,
                            sample_index=i,
                            model_id=model_cfg["id"],
                            input_text=input_str,
                            output_text=f"ERROR: {str(last_error)}",
                            scores={},
                            result_metadata={"error": str(last_error)},
                        ))
                        thread_session.commit()

                    # Update shared progress
                    with progress_lock:
                        model_progress[mid] += 1
                        processed_total[0] += 1
                        current_processed = processed_total[0]

                    # Publish progress (outside lock to avoid blocking)
                    publish_progress(make_progress_payload(
                        f"{model_cfg['name']}: 已完成 {current_processed}/{total}"
                    ))

                    # Update task progress in DB every sample
                    try:
                        with progress_lock:
                            pct = int(processed_total[0] / total * 100) if total > 0 else 0
                            ps = processed_total[0]
                        thread_session.execute(
                            sa_text("UPDATE evaluation_tasks SET progress = :p, processed_samples = :ps WHERE id = :tid"),
                            {"p": pct, "ps": ps, "tid": task_id},
                        )
                        thread_session.commit()
                    except Exception as exc:
                        thread_session.rollback()
                        print(f"[WARN] Failed to update progress for task {task_id}: {exc}")

            finally:
                thread_session.close()
                thread_engine_db.dispose()

            return mid, model_results

        # --- Run models in parallel ---
        results_by_model = {str(mc["id"]): [] for mc in model_configs}
        num_workers = min(len(model_configs), 4)  # Cap at 4 threads

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(evaluate_model, mc): mc for mc in model_configs}
            for future in as_completed(futures):
                mc = futures[future]
                try:
                    mid, model_results = future.result()
                    results_by_model[mid] = model_results
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    # Model failed entirely, continue with others
                    publish_progress(make_progress_payload(
                        f"模型 {mc['name']} 评测出错: {str(e)[:100]}"
                    ))

        # All model threads done — update progress to 99% while aggregating
        task = session.get(EvaluationTask, task_id)
        task.processed_samples = total  # all samples are done
        task.progress = 99
        session.commit()
        publish_progress(make_progress_payload("所有样本已完成，正在汇总结果..."))

        # --- Aggregate results from DB (authoritative source) ---
        from sqlalchemy import func as sa_func, select as sa_select
        summary = {"by_model": {}}
        for model_cfg in model_configs:
            mid = str(model_cfg["id"])

            # Count from DB
            db_count = session.query(sa_func.count(EvaluationResult.id)).filter(
                EvaluationResult.task_id == task_id,
                EvaluationResult.model_id == model_cfg["id"],
            ).scalar() or 0

            # Get all results from DB for score aggregation
            db_results = session.query(EvaluationResult).filter(
                EvaluationResult.task_id == task_id,
                EvaluationResult.model_id == model_cfg["id"],
            ).all()

            if not db_results:
                continue

            agg_scores = {}
            latencies = []
            for r in db_results:
                for key, val in (r.scores or {}).items():
                    if isinstance(val, (int, float)):
                        agg_scores.setdefault(key, []).append(val)
                if r.latency_ms:
                    latencies.append(r.latency_ms)

            avg_scores = {k: sum(v) / len(v) for k, v in agg_scores.items()}

            summary["by_model"][mid] = {
                "model_name": model_cfg["name"],
                "scores": avg_scores,
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                "sample_count": db_count,
            }

        # Update ELO if multiple models
        if len(model_configs) > 1:
            _update_elo_scores(session, model_configs, summary)

        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        task.results_summary = summary
        task.progress = 100
        session.commit()

        publish_progress({"status": "completed", "progress": 100, "summary": summary})
        return summary

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        try:
            session.rollback()
            task = session.get(EvaluationTask, task_id)
            if task:
                task.status = "failed"
                task.error_message = str(e)[:2000]
                session.commit()
        except Exception:
            pass
        publish_progress({"status": "failed", "error": str(e)})
        raise
    finally:
        session.close()
        try:
            redis_client.close()
        except Exception:
            pass


def _update_elo_scores(session, model_configs: list, summary: dict):
    """Update ELO ratings based on evaluation results."""
    from app.db.models import ModelEloScore

    K = 32  # ELO K-factor
    scores_map = {}
    for mc in model_configs:
        mid = str(mc["id"])
        model_summary = summary["by_model"].get(mid, {})
        model_scores = model_summary.get("scores", {})
        if model_scores:
            avg = sum(model_scores.values()) / len(model_scores)
        else:
            avg = 0
        scores_map[mc["id"]] = avg

    # Round-robin ELO updates
    model_ids = list(scores_map.keys())
    for i in range(len(model_ids)):
        for j in range(i + 1, len(model_ids)):
            mid_a, mid_b = model_ids[i], model_ids[j]
            score_a = scores_map[mid_a]
            score_b = scores_map[mid_b]

            elo_a = session.query(ModelEloScore).filter_by(model_config_id=mid_a).first()
            elo_b = session.query(ModelEloScore).filter_by(model_config_id=mid_b).first()

            if not elo_a or not elo_b:
                continue

            # Expected scores
            ea = 1 / (1 + 10 ** ((elo_b.elo_score - elo_a.elo_score) / 400))
            eb = 1 - ea

            # Actual outcomes
            if score_a > score_b:
                sa, sb = 1.0, 0.0
                elo_a.wins += 1
                elo_b.losses += 1
            elif score_b > score_a:
                sa, sb = 0.0, 1.0
                elo_b.wins += 1
                elo_a.losses += 1
            else:
                sa, sb = 0.5, 0.5
                elo_a.draws += 1
                elo_b.draws += 1

            elo_a.elo_score += K * (sa - ea)
            elo_b.elo_score += K * (sb - eb)
            elo_a.total_matches += 1
            elo_b.total_matches += 1

    session.commit()
