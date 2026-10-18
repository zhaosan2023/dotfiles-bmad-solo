"""控制器运行资产与离线任务实现的边界反例；不启动 Pi、不联网。

在临时工作区用合成模块文件验证绑定边界，绝不改动实际活动控制器。
离线裁决器仍须由任务显式实现输入和独立验证负责验收。
"""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_agent_backend as agent
import bmad_loop as loop
import test_batch_guards as fixtures


class ControllerAssetScopeGuards(unittest.TestCase):
    def test_offline_checker_can_change_but_live_controller_change_blocks_verification(self):
        for target, verification_expected in (
            ("bmad_pi_evidence.py", True),
            ("bmad_loop.py", False),
            ("bmad_supervisor.py", False),
        ):
            with self.subTest(target=target):
                guards = fixtures.BatchGuards(
                    "test_budget_exhaustion_stops_new_calls_and_preserves_changes")
                self.addCleanup(guards.doCleanups)
                guards.setUp()
                program = guards.root / "synthetic-controller/scripts"
                program.mkdir(parents=True)
                for name in ("bmad_pi_evidence.py", "bmad_loop.py", "bmad_supervisor.py"):
                    (program / name).write_text("# synthetic binding asset; never imported\n")

                def intercepted_call(**options):
                    (program / target).write_text("# retained synthetic implementation change\n")
                    return {
                        "operation": "agent-call", "status": "PASS", "reason": "",
                        "returncode": 0, "cleanup_ok": True,
                        "cancelled": False, "timed_out": False, "category": "OK",
                    }

                spec = loop.LoopSpec(
                    workspace=guards.root, plan_file="plan.md",
                    request_file="T1-request.json", backend="headless",
                    backend_config="backend.json", maximum_rounds=1,
                    maximum_calls=1, timeout_seconds=12, no_progress_rounds=6,
                )
                with patch.dict(os.environ, {fixtures.CREDENTIAL: "synthetic-only"}), \
                        patch.object(loop, "__file__", str(program / "bmad_loop.py")), \
                        patch.object(agent, "invoke", side_effect=intercepted_call) as invoke:
                    result = loop.start(spec)
                invoke.assert_called_once()
                self.assertEqual(result["status"], "BLOCKED", result)
                self.assertTrue(result["cleanup_ok"], result)
                self.assertFalse(loop.writer_active(guards.root))
                self.assertEqual(result["completed_tasks"], [])
                if verification_expected:
                    self.assertIsNotNone(result["last_verdict"], result)
                    self.assertIn("最大轮次", result["reason"])
                else:
                    self.assertIsNone(result["last_verdict"], result)
                    self.assertIn("绑定契约或驱动变化", result["reason"])
                self.assertIn("retained", (program / target).read_text())


if __name__ == "__main__":
    unittest.main()
