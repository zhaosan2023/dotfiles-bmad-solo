"""真实公共部署产物的 V5 来源绑定；仅操作项目内夹具与临时根。

不启动 Agent、不激活真实宿主；分发来源一致性与协作锁不能替代
任务期循环、取消清理、宿主模式语义或远程断开验收。
"""
from pathlib import Path
import sys
import unittest

import test_gitops_dry_run as fixtures
import test_suite_selection as selection

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))
from bmad_suite_source import bound_suite
from bmad_supervisor import SupervisorError


class SuiteSourceDeployment(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    add_v5 = selection.SuiteSelection.add_v5
    deploy = selection.SuiteSelection.deploy
    MANIFEST = selection.SuiteSelection.MANIFEST

    def install_v5(self):
        self.add_v5()
        return self.deploy("v5")

    def test_actual_deployment_binds_read_only_and_blocks_public_writer(self):
        manifest = self.install_v5()
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        before_home = self.tree(self.home)
        with bound_suite(self.target) as binding:
            self.assertEqual(binding.suite_root,
                             self.target / ".gemini/config/plugins/bmad-suite")
            self.assertEqual(binding._snapshot["source_commit"],
                             manifest["source_commit"])
            self.assertEqual(binding._snapshot["source_dirty"],
                             manifest["source_dirty"])
            binding.check()
            result = self.run_command(["bash", "bs.sh", "v4"])
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("另一部署进程持有锁", result.stderr)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertEqual(self.tree(self.home), before_home)
        switched = self.deploy("v4")
        self.assertEqual(switched["major_version"], "v4")

    def test_deployed_binding_module_is_self_contained_in_isolated_python(self):
        self.install_v5()
        plugin = self.target / ".gemini/config/plugins/bmad-suite"
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        before_home = self.tree(self.home)
        program = (
            "import pathlib, sys; "
            "sys.path.insert(0, sys.argv[1]); "
            "from bmad_suite_source import bound_suite; "
            "root=pathlib.Path(sys.argv[2]); "
            "lease=bound_suite(root); binding=lease.__enter__(); "
            "binding.check(); "
            "assert binding.suite_root == root / '.gemini/config/plugins/bmad-suite'; "
            "lease.__exit__(None, None, None); "
            "print('PASS: deployed V5 source binding; no Agent started')"
        )
        result = self.run_command([
            sys.executable, "-I", "-B", "-c", program,
            str(plugin / "scripts"), str(self.target),
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: deployed V5 source binding", result.stdout)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertEqual(self.tree(self.home), before_home)

    def test_boundary_detects_deployed_runtime_edit_without_restoring_user_change(self):
        self.install_v5()
        path = self.target / ".gemini/config/plugins/bmad-suite/scripts/bmad-exec.py"
        changed = path.read_bytes() + b"\n# external user change\n"
        before_repo = self.tree(self.repo)
        before_home = self.tree(self.home)
        with self.assertRaisesRegex(SupervisorError, "摘要不一致"):
            with bound_suite(self.target):
                path.write_bytes(changed)
        self.assertEqual(path.read_bytes(), changed)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.home), before_home)
        before_target = self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "v4"])
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("bmad-exec.py", result.stdout + result.stderr)
        self.assertEqual(self.tree(self.target), before_target)

    def test_actual_v4_deployment_is_not_silently_adopted(self):
        self.deploy("v4")
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        before_home = self.tree(self.home)
        with self.assertRaisesRegex(SupervisorError, "明确为 V5"):
            with bound_suite(self.target):
                self.fail("V4 不得作为 V5 活动来源进入任务")
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertEqual(self.tree(self.home), before_home)


if __name__ == "__main__":
    unittest.main()
