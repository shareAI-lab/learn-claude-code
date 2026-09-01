import asyncio
import importlib.util
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TRACE_RUNTIME = load_module(
    "trace_runtime_test_module",
    ROOT / "s15_integrated_harness" / "trace_runtime.py",
)
TRACE_VIEW = load_module(
    "trace_view_test_module",
    ROOT / "s15_integrated_harness" / "trace_view.py",
)


def read_events(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class FakeMessages:
    def __init__(self):
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", thinking="private reasoning"),
                SimpleNamespace(
                    type="tool_use", id="toolu_1", name="read_file",
                    input={"path": "README.md"},
                ),
            ],
            stop_reason="tool_use",
            usage=SimpleNamespace(
                input_tokens=123,
                output_tokens=45,
                cache_creation_input_tokens=6,
                cache_read_input_tokens=7,
            ),
        )


class TraceRuntimeTests(unittest.TestCase):
    def test_model_boundary_records_metadata_without_prompt_or_reasoning(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = TRACE_RUNTIME.TraceRecorder(
                Path(directory), "test", preview_chars=20
            )
            raw = SimpleNamespace(messages=FakeMessages())
            client = TRACE_RUNTIME.wrap_client(raw, recorder)
            with recorder.agent_scope("agent-root", None, "lead"):
                with recorder.model_scope("lead"):
                    client.messages.create(
                        model="Qwen/Qwen3.8-27B",
                        system="system-marker-that-must-not-be-stored",
                        messages=[{
                            "role": "user",
                            "content": "prompt-marker-that-must-not-be-stored",
                        }],
                        tools=[{"name": "read_file"}],
                        max_tokens=100,
                    )
            path = recorder.path
            recorder.finish_run()

            events = read_events(path)
            self.assertEqual(path.stat().st_mode & 0o077, 0)
            self.assertEqual(events[0]["event"], "run_start")
            self.assertEqual(events[-1]["event"], "run_end")
            request = next(event for event in events if event["event"] == "model_request")
            response = next(event for event in events if event["event"] == "model_response")
            self.assertEqual(request["agent_id"], "agent-root")
            self.assertEqual(request["data"]["purpose"], "lead")
            self.assertEqual(request["span_id"], response["span_id"])
            self.assertEqual(response["data"]["usage"]["input_tokens"], 123)
            self.assertEqual(
                response["data"]["requested_actions"][0]["type"], "thinking"
            )
            self.assertEqual(
                response["data"]["requested_actions"][1]["tool"], "read_file"
            )
            serialized = path.read_text(encoding="utf-8")
            self.assertNotIn("prompt-marker-that-must-not-be-stored", serialized)
            self.assertNotIn("system-marker-that-must-not-be-stored", serialized)
            self.assertNotIn("private reasoning", serialized)

    def test_recursive_secret_redaction_and_bounded_output_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = TRACE_RUNTIME.TraceRecorder(
                Path(directory), "test", preview_chars=8
            )
            recorder.emit("example", {
                "api_key": "do-not-store",
                "nested": {"Authorization": "Bearer secret", "count": 2},
                "command": (
                    "curl -H 'Authorization: Bearer embedded-secret' "
                    "https://user:password@example.test; "
                    "ANTHROPIC_API_KEY=sk-ant-embedded12345"
                ),
                "long": "x" * 3000,
            })
            summary = recorder.summarize_output(
                "abcdefghijk Authorization: Bearer output-secret"
            )
            recorder.emit("summary", {"result": summary})
            path = recorder.path
            recorder.finish_run()

            example = next(event for event in read_events(path)
                           if event["event"] == "example")
            self.assertEqual(example["data"]["api_key"], "[REDACTED]")
            self.assertEqual(example["data"]["nested"]["Authorization"], "[REDACTED]")
            self.assertEqual(example["data"]["nested"]["count"], 2)
            self.assertTrue(example["data"]["long"]["truncated"])
            self.assertEqual(summary["preview"], "abcdefgh")
            serialized = path.read_text(encoding="utf-8")
            for secret in (
                "do-not-store", "embedded-secret", "password",
                "sk-ant-embedded12345", "output-secret",
            ):
                self.assertNotIn(secret, serialized)

    def test_concurrent_writers_produce_valid_unique_jsonl_records(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = TRACE_RUNTIME.TraceRecorder(Path(directory), "test")

            def write(worker):
                with recorder.agent_scope(f"agent-{worker}", "agent-root", "test"):
                    for index in range(30):
                        recorder.emit("tick", {"worker": worker, "index": index})

            threads = [threading.Thread(target=write, args=(index,)) for index in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            path = recorder.path
            closers = [
                threading.Thread(target=recorder.finish_run)
                for _index in range(4)
            ]
            for thread in closers:
                thread.start()
            for thread in closers:
                thread.join()

            events = read_events(path)
            ticks = [event for event in events if event["event"] == "tick"]
            self.assertEqual(len(ticks), 120)
            self.assertEqual(
                sum(event["event"] == "run_end" for event in events), 1
            )
            self.assertEqual(len({event["event_id"] for event in events}), len(events))
            self.assertEqual({event["agent_id"] for event in ticks},
                             {"agent-0", "agent-1", "agent-2", "agent-3"})

    def test_viewer_calculates_parallelism_and_renders_both_views(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = TRACE_RUNTIME.TraceRecorder(Path(directory), "test")
            ready = threading.Barrier(3)
            release = threading.Event()

            def model_call(agent_id):
                recorder.emit(
                    "agent_create", {"role": "worker", "task": agent_id},
                    agent_id=agent_id, parent_agent_id="agent-root",
                    agent_kind="test",
                )
                with recorder.agent_scope(agent_id, "agent-root", "test"):
                    with recorder.span(
                        "model_request", "model_response",
                        {"purpose": "test", "model": "fake"},
                    ) as span:
                        ready.wait(timeout=2)
                        release.wait(timeout=2)
                        span.finish(
                            purpose="test", model="fake", requested_actions=[],
                            usage={"input_tokens": 10, "output_tokens": 2},
                        )

            threads = [
                threading.Thread(target=model_call, args=(f"agent-{index}",))
                for index in range(2)
            ]
            for thread in threads:
                thread.start()
            ready.wait(timeout=2)
            time.sleep(0.01)
            release.set()
            for thread in threads:
                thread.join()
            with recorder.agent_scope("agent-root", None, "lead"):
                with recorder.span(
                    "tool_start", "tool_end",
                    {"tool": "read_file", "arguments": {"path": "README.md"}},
                ) as tool_span:
                    with recorder.span(
                        "permission_wait_start", "permission_wait_end",
                        {"tool": "read_file"},
                    ):
                        time.sleep(0.002)
                    with recorder.span(
                        "tool_execution_start", "tool_execution_end",
                        {"tool": "read_file"},
                    ) as execution_span:
                        time.sleep(0.001)
                        execution_span.finish(status="ok", tool="read_file")
                    tool_span.finish(status="ok", tool="read_file")
            path = recorder.path
            recorder.finish_run()

            events = TRACE_VIEW.load_trace(path)
            metrics = TRACE_VIEW.calculate_metrics(events)
            self.assertEqual(metrics["total_model_calls"], 2)
            self.assertEqual(metrics["total_tool_calls"], 1)
            self.assertEqual(metrics["total_subagents"], 2)
            self.assertEqual(metrics["maximum_agent_depth"], 1)
            self.assertEqual(metrics["maximum_parallel_agents"], 2)
            self.assertEqual(metrics["input_tokens"], 20)
            self.assertGreater(metrics["tool_time_ms"], 0)
            self.assertGreater(metrics["human_wait_ms"], 0)
            self.assertIn("Root Agent", TRACE_VIEW.render_tree(events))
            self.assertIn("LLM [test]", TRACE_VIEW.render_tree(events))
            timeline = TRACE_VIEW.render_timeline(events, width=50)
            self.assertIn("Timeline", timeline)
            self.assertIn("M=model", timeline)


class WorkflowTraceTests(unittest.TestCase):
    def test_pipeline_records_parentage_and_stage_dependencies(self):
        workflow = load_module(
            "workflow_trace_test_module",
            ROOT / "s16_workflow_runtime" / "code.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            workflow.STORE = temporary / "runtime"
            recorder = TRACE_RUNTIME.TraceRecorder(temporary / "traces", "workflow-test")
            workflow.TRACE_OBSERVER = recorder

            async def direct_to_thread(function, *args, **kwargs):
                return function(*args, **kwargs)

            meta = {
                "name": "trace-pipeline",
                "description": "two items through fan-out and fan-in stages",
                "phases": ["one", "fan-out", "join"],
            }

            async def script(ctx, _args):
                async def first(_value, item, _index):
                    return await ctx.agent(
                        f"first {item}", label=f"first:{item}", phase="one"
                    )

                async def fan_out(value, item, _index):
                    return await ctx.parallel([
                        lambda: ctx.agent(
                            f"left {item} after {value}",
                            label=f"left:{item}", phase="fan-out",
                        ),
                        lambda: ctx.agent(
                            f"right {item} after {value}",
                            label=f"right:{item}", phase="fan-out",
                        ),
                    ])

                async def join(value, item, _index):
                    return await ctx.agent(
                        f"join {item} after {value}",
                        label=f"join:{item}", phase="join",
                    )

                return await ctx.pipeline(["a", "b"], first, fan_out, join)

            with recorder.agent_scope("agent-root", None, "lead"):
                with mock.patch.object(workflow.asyncio, "to_thread", direct_to_thread):
                    result = asyncio.run(
                        workflow.WorkflowTool().call(meta, script, args={})
                    )
            self.assertEqual(result["task"].status, "completed")
            run_id = result["task"].run_id

            initial_events = read_events(recorder.path)
            initial_workers = [
                event for event in initial_events
                if event["event"] == "agent_create"
                and event["data"].get("role") == "workflow-agent"
            ]
            self.assertEqual(len(initial_workers), 8)
            self.assertEqual(
                {worker["parent_agent_id"] for worker in initial_workers},
                {next(
                    event["agent_id"] for event in initial_events
                    if event["event"] == "agent_create"
                    and event["data"].get("role") == "workflow-orchestrator"
                )},
            )

            queued = [
                event["data"] for event in initial_events
                if event["event"] == "workflow_node_queued"
            ]
            by_item_stage = {}
            for node in queued:
                by_item_stage.setdefault(
                    (node["item_index"], node["stage_index"]), []
                ).append(node)
            for item_index in (0, 1):
                first_nodes = by_item_stage[(item_index, 0)]
                fan_nodes = by_item_stage[(item_index, 1)]
                join_nodes = by_item_stage[(item_index, 2)]
                self.assertEqual(len(first_nodes), 1)
                self.assertEqual(len(fan_nodes), 2)
                self.assertEqual(len(join_nodes), 1)
                first_id = first_nodes[0]["workflow_node_id"]
                fan_ids = {node["workflow_node_id"] for node in fan_nodes}
                self.assertTrue(all(
                    node["depends_on_node_ids"] == [first_id]
                    for node in fan_nodes
                ))
                self.assertEqual(
                    set(join_nodes[0]["depends_on_node_ids"]), fan_ids
                )

            dependencies = [
                event["data"] for event in initial_events
                if event["event"] == "workflow_dependency"
            ]
            self.assertEqual(len(dependencies), 8)
            starts = {
                event["span_id"] for event in initial_events
                if event["event"] == "workflow_node_start"
            }
            ends = {
                event["span_id"] for event in initial_events
                if event["event"] == "workflow_node_end"
            }
            self.assertEqual(starts, ends)

            with recorder.agent_scope("agent-root", None, "lead"):
                with mock.patch.object(workflow.asyncio, "to_thread", direct_to_thread):
                    resumed = asyncio.run(
                        workflow.WorkflowTool().call(
                            meta, script, args={}, resume_from_run_id=run_id
                        )
                    )
            self.assertEqual(resumed["task"].status, "completed")
            self.assertEqual(resumed["task"].usage["agents"], 0)
            path = recorder.path
            recorder.finish_run()

            events = read_events(path)
            creates = [
                event for event in events
                if event["event"] == "agent_create"
            ]
            orchestrators = [
                event for event in creates
                if event["data"].get("role") == "workflow-orchestrator"
            ]
            workers = [
                event for event in creates
                if event["data"].get("role") == "workflow-agent"
            ]
            self.assertEqual(len(orchestrators), 2)
            self.assertEqual(len(workers), 16)
            cached_starts = [
                event for event in events
                if event["event"] == "workflow_node_start"
                and event["data"].get("executed") is False
            ]
            cached_ends = [
                event for event in events
                if event["event"] == "workflow_node_end"
                and event["data"].get("executed") is False
            ]
            self.assertEqual(len(cached_starts), 8)
            self.assertEqual(
                {event["span_id"] for event in cached_starts},
                {event["span_id"] for event in cached_ends},
            )
            self.assertTrue(all(
                event["data"]["status"] == "cached" for event in cached_ends
            ))
            metrics = TRACE_VIEW.calculate_metrics(events)
            self.assertEqual(metrics["cached_workflow_nodes"], 8)
            tree = TRACE_VIEW.render_tree(events)
            self.assertIn("Workflow node: join:a", tree)
            self.assertIn("journal cache", tree)
            timeline = TRACE_VIEW.render_timeline(events, width=60)
            self.assertIn("Dependencies:", timeline)


if __name__ == "__main__":
    unittest.main()
