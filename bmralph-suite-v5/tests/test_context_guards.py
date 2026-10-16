"""受控上下文预算反例；不证明宿主旁路、新会话或远程运行时。

使用明确的本地数据夹具；输入和累计工具输出分别计入 JSON 字节开销。
测试不安装依赖、不迁移活动计划、不保存第二份任务进度。
"""
import copy
import json
from pathlib import Path
import sys
import unittest


SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_context as context


class ContextGuards(unittest.TestCase):
    def setUp(self):
        view = "计划：CONTEXT-LOCAL-01\nT1 [READY] 当前任务\nT2 [PENDING] 未完成依赖任务\n"
        self.projection = {
            "operation": "render-state", "status": "READY",
            "plan_id": "CONTEXT-LOCAL-01", "plan_file": "plan.md",
            "view": view, "view_lines": len(view.splitlines()),
            "view_bytes": len(view.encode("utf-8")),
            "tasks_total": 2, "unfinished_count": 2,
            "ready_tasks": ["T1"],
            "business_reexecuted": False, "state_saved": False,
        }
        self.arguments = {
            "goal": "保留约束并完成当前获准任务",
            "authorization": "仅项目内本地实施；不启动远程任务或提交",
            "task": {
                "task_id": "T1", "title": "当前获准任务",
                "verification": {"operation": "unit-test"},
            },
            "state_projection": self.projection,
            "constraints": ("不修改对照源码",),
            "capabilities": ("按需读取当前源码与测试",),
            "code": ("VALUE = 1\n",),
            "unfinished_changes": ("保留未提交修改",),
            "feedback": ("最近有效失败：断言尚未通过",),
        }

    def assemble(self, **changes):
        arguments = copy.deepcopy(self.arguments)
        arguments.update(changes)
        before = copy.deepcopy(arguments)
        result = context.assemble_input(**arguments)
        self.assertEqual(arguments, before)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["controlled_bytes"], len(result["payload"].encode("utf-8")))
        return result

    def test_all_necessary_parts_and_unfinished_tasks_survive_assembly(self):
        result = self.assemble()
        decoded = json.loads(result["payload"])
        for name in ("goal", "authorization", "task", "state_projection"):
            self.assertEqual(decoded[name], self.arguments[name])
        for name in ("constraints", "capabilities", "code", "unfinished_changes", "feedback"):
            self.assertEqual(decoded[name], list(self.arguments[name]))
        self.assertIn("T2 [PENDING]", decoded["state_projection"]["view"])
        self.assertIn("断言尚未通过", decoded["feedback"][0])

    def test_unknown_host_input_is_disclosed_not_claimed_as_full_coverage(self):
        result = self.assemble()
        decoded = json.loads(result["payload"])
        self.assertEqual(result["host_input_coverage"], "UNKNOWN")
        self.assertIsNone(decoded["observed_host_bytes"])
        self.assertIn("不能声称整个请求", decoded["host_observation"])
        self.assertIn("不是 Token", decoded["measurement"])
        self.assertEqual(result["accounted_bytes"], result["controlled_bytes"])

    def test_observed_host_bytes_count_without_claiming_complete_observation(self):
        result = self.assemble(observed_host_bytes=1000)
        self.assertEqual(result["accounted_bytes"], result["controlled_bytes"] + 1000)
        self.assertEqual(result["host_input_coverage"], "PARTIAL_OBSERVATION")
        self.assertIn("不证明全部", json.loads(result["payload"])["host_observation"])

    def test_zero_observed_host_bytes_is_distinct_from_unknown(self):
        result = self.assemble(observed_host_bytes=0)
        self.assertEqual(result["host_input_coverage"], "PARTIAL_OBSERVATION")
        self.assertEqual(result["accounted_bytes"], result["controlled_bytes"])

    def test_exact_startup_boundary_passes_and_one_byte_less_blocks(self):
        first = self.assemble()
        size = first["accounted_bytes"]
        self.assertEqual(self.assemble(maximum_bytes=size)["accounted_bytes"], size)
        with self.assertRaises(context.ContextBlocked):
            self.assemble(maximum_bytes=size - 1)

    def test_observed_host_overflow_blocks_without_dropping_controlled_input(self):
        with self.assertRaises(context.ContextBlocked):
            self.assemble(observed_host_bytes=context.DEFAULT_STARTUP_BYTES)

    def test_long_single_line_and_multibyte_input_are_not_silently_cut(self):
        for value in ("x" * 100000, "中文" * 20000, "\\" * 50000):
            with self.subTest(kind=value[:2]):
                with self.assertRaises(context.ContextBlocked):
                    self.assemble(code=(value,))

    def test_json_escaping_is_part_of_startup_budget(self):
        value = "\\" * 1000
        result = self.assemble(code=(value,))
        decoded = json.loads(result["payload"])
        self.assertEqual(decoded["code"], [value])
        self.assertGreater(result["controlled_bytes"], len(value.encode("utf-8")) * 2)

    def test_invalid_startup_or_host_budgets_are_rejected(self):
        changes = (
            {"maximum_bytes": True}, {"maximum_bytes": 255},
            {"maximum_bytes": context.MAX_STARTUP_BYTES + 1},
            {"observed_host_bytes": True}, {"observed_host_bytes": -1},
            {"observed_host_bytes": "unknown"},
        )
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(context.ContextBlocked):
                    self.assemble(**change)

    def test_required_text_and_explicit_item_types_are_checked(self):
        for changes in (
            {"goal": " "}, {"authorization": ""}, {"goal": "hidden\x00text"},
            {"code": ["implicit list"]}, {"feedback": ("",)},
            {"capabilities": ("entry\x00",)}, {"constraints": (None,)},
            {"unfinished_changes": tuple("change" for _ in range(257))},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(context.ContextBlocked):
                    self.assemble(**changes)

    def test_unique_task_shape_and_dependency_readiness_are_required(self):
        for task in (
            {}, {"task_id": "T1", "title": "missing verification"},
            {"task_id": "T2", "title": "not ready", "verification": {}},
            {"task_id": "T1", "title": "task", "verification": [],},
            {"task_id": "T1", "title": "task", "verification": {}, "extra": "task"},
        ):
            with self.subTest(task=task):
                with self.assertRaises(context.ContextBlocked):
                    self.assemble(task=task)

    def test_blocked_suspended_or_completed_projection_is_not_resumed(self):
        for status in ("BLOCKED", "SUSPENDED", "COMPLETED"):
            projection = copy.deepcopy(self.projection)
            projection["status"] = status
            with self.subTest(status=status):
                with self.assertRaises(context.ContextBlocked):
                    self.assemble(state_projection=projection)

    def test_projection_counts_and_readonly_flags_must_match(self):
        for changes in (
            {"view_lines": 79}, {"view_bytes": 1},
            {"tasks_total": True}, {"unfinished_count": 3},
            {"unfinished_count": 0}, {"ready_tasks": []},
            {"ready_tasks": [None]}, {"plan_id": ""},
            {"plan_file": ""}, {"business_reexecuted": True},
            {"state_saved": True}, {"operation": "unverified-state"},
        ):
            with self.subTest(changes=changes):
                projection = copy.deepcopy(self.projection)
                projection.update(changes)
                with self.assertRaises(context.ContextBlocked):
                    self.assemble(state_projection=projection)

    def test_eighty_lines_do_not_replace_total_startup_budget(self):
        projection = copy.deepcopy(self.projection)
        view = "状态\n" * 80
        projection.update(view=view, view_lines=80, view_bytes=len(view.encode("utf-8")))
        self.assemble(state_projection=projection)
        with self.assertRaises(context.ContextBlocked):
            self.assemble(state_projection=projection, code=("necessary code" * 10000,))
        projection["view"] += "额外任务\n"
        projection["view_lines"] = 81
        projection["view_bytes"] = len(projection["view"].encode("utf-8"))
        with self.assertRaises(context.ContextBlocked):
            self.assemble(state_projection=projection)

    def test_nonfinite_or_unserializable_task_data_blocks(self):
        for value in (float("nan"), float("inf"), object()):
            task = copy.deepcopy(self.arguments["task"])
            task["verification"]["invalid"] = value
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(context.ContextBlocked):
                    self.assemble(task=task)

    def test_tool_payload_is_preserved_and_json_bytes_are_counted(self):
        budget = context.ToolOutputBudget()
        result = {"status": "PASS", "operation": "unit-test", "tests_run": 2,
                  "verdict_path": "evidence/run.verdict.json"}
        before = copy.deepcopy(result)
        payload = budget.consume(result)
        self.assertEqual(json.loads(payload), result)
        self.assertEqual(result, before)
        self.assertEqual(budget.accepted_bytes, len(payload.encode("utf-8")))
        self.assertEqual(budget.accepted_calls, 1)
        self.assertIs(budget.blocked, False)

    def test_business_failure_survives_successful_summary_serialization(self):
        budget = context.ToolOutputBudget()
        result = {"status": "BLOCKED", "reason": "真实断言失败",
                  "log_saved": True, "verdict_path": "evidence/failed.verdict.json"}
        forwarded = json.loads(budget.consume(result))
        self.assertEqual(forwarded["status"], "BLOCKED")
        self.assertEqual(forwarded["reason"], "真实断言失败")
        self.assertIs(forwarded["log_saved"], True)
        self.assertIs(budget.blocked, False)

    def test_all_supported_business_states_are_preserved_without_promotion(self):
        for status in ("PASS", "READY", "SUSPENDED", "COMPLETED"):
            with self.subTest(status=status):
                budget = context.ToolOutputBudget()
                self.assertEqual(json.loads(budget.consume({"status": status}))["status"], status)

    def test_many_small_tool_results_exhaust_cumulative_budget(self):
        budget = context.ToolOutputBudget(maximum_bytes=512, maximum_result_bytes=256)
        result = {"status": "PASS", "detail": "small result"}
        size = len(context.encode_object(result).encode("utf-8"))
        count = 512 // size
        for _ in range(count):
            budget.consume(result)
        self.assertEqual(budget.accepted_calls, count)
        self.assertEqual(budget.accepted_bytes, count * size)
        with self.assertRaises(context.ContextBlocked):
            budget.consume(result)
        self.assertIs(budget.blocked, True)
        self.assertEqual(budget.accepted_bytes, count * size)
        with self.assertRaises(context.ContextBlocked):
            budget.consume({"status": "PASS"})

    def test_exact_single_result_boundary_passes_then_smaller_budget_blocks(self):
        result = {"status": "PASS", "detail": "x" * 300}
        size = len(context.encode_object(result).encode("utf-8"))
        budget = context.ToolOutputBudget(maximum_bytes=size, maximum_result_bytes=size)
        self.assertEqual(len(budget.consume(result).encode("utf-8")), size)
        failed = context.ToolOutputBudget(maximum_bytes=size, maximum_result_bytes=size - 1)
        with self.assertRaises(context.ContextBlocked):
            failed.consume(result)
        self.assertIs(failed.blocked, True)
        self.assertEqual(failed.accepted_bytes, 0)
        self.assertEqual(failed.accepted_calls, 0)

    def test_tool_result_multibyte_and_escaping_are_counted(self):
        for value in ("中文" * 100, "\\" * 200):
            with self.subTest(value=value[:2]):
                budget = context.ToolOutputBudget(maximum_bytes=1024, maximum_result_bytes=256)
                with self.assertRaises(context.ContextBlocked):
                    budget.consume({"status": "PASS", "detail": value})
                self.assertIs(budget.blocked, True)

    def test_invalid_tool_result_latches_blocked_without_consuming_budget(self):
        for result in (
            None, [], {}, {"status": "UNKNOWN"},
            {"status": "BLOCKED"}, {"status": "BLOCKED", "reason": " "},
            {"status": "PASS", "detail": float("nan")},
            {"status": "PASS", "detail": object()},
        ):
            with self.subTest(kind=type(result).__name__):
                budget = context.ToolOutputBudget()
                with self.assertRaises(context.ContextBlocked):
                    budget.consume(result)
                self.assertIs(budget.blocked, True)
                self.assertEqual(budget.accepted_bytes, 0)
                self.assertEqual(budget.accepted_calls, 0)

    def test_unhashable_tool_status_fails_closed_and_latches_blocked(self):
        for status in ([], {}):
            with self.subTest(status=status):
                budget = context.ToolOutputBudget()
                with self.assertRaises(context.ContextBlocked):
                    budget.consume({"status": status})
                self.assertIs(budget.blocked, True)
                self.assertEqual(budget.accepted_bytes, 0)

    def test_invalid_unicode_is_a_budget_block_not_uncaught_serialization_error(self):
        with self.assertRaises(context.ContextBlocked):
            self.assemble(code=("invalid surrogate: \ud800",))
        budget = context.ToolOutputBudget()
        with self.assertRaises(context.ContextBlocked):
            budget.consume({"status": "PASS", "detail": "\ud800"})
        self.assertIs(budget.blocked, True)
        self.assertEqual(budget.accepted_bytes, 0)

    def test_budget_configuration_cannot_import_history_or_increase_hard_caps(self):
        for values in (
            {"maximum_bytes": True}, {"maximum_bytes": 255},
            {"maximum_bytes": context.MAX_CUMULATIVE_TOOL_BYTES + 1},
            {"maximum_result_bytes": context.MAX_TOOL_RESULT_BYTES + 1},
            {"maximum_result_bytes": True},
            {"maximum_bytes": 256, "maximum_result_bytes": 512},
            {"accepted_bytes": 1}, {"accepted_calls": 1}, {"blocked": True},
        ):
            with self.subTest(values=values):
                with self.assertRaises(context.ContextBlocked):
                    context.ToolOutputBudget(**values)

    def test_separate_round_instances_start_with_separate_counters(self):
        first = context.ToolOutputBudget()
        second = context.ToolOutputBudget()
        first.consume({"status": "PASS"})
        self.assertEqual(first.accepted_calls, 1)
        self.assertEqual(second.accepted_calls, 0)
        self.assertEqual(second.accepted_bytes, 0)
        self.assertIs(second.blocked, False)


    def test_invalid_unicode_in_state_view_is_a_context_block(self):
        projection = copy.deepcopy(self.projection)
        projection.update(view="invalid surrogate: \ud800\n", view_lines=1, view_bytes=1)
        with self.assertRaises(context.ContextBlocked):
            self.assemble(state_projection=projection)

    def test_boolean_state_view_counts_cannot_match_integer_counts(self):
        for changes in (
            {"view": "x", "view_lines": True, "view_bytes": 1},
            {"view": "x", "view_lines": 1, "view_bytes": True},
        ):
            with self.subTest(changes=changes):
                projection = copy.deepcopy(self.projection)
                projection.update(changes)
                with self.assertRaises(context.ContextBlocked):
                    self.assemble(state_projection=projection)


if __name__ == "__main__":
    unittest.main()
