"""运行候选副本的相关本地反例；不启动 Agent 或激活真实宿主。

合成部署根使用当前 V5 的物理程序资产；仅核验候选创建和版本
隔离，不把这些测试视为任务循环租约、取消或真实运行时通过。
"""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_suite_source as fixtures

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_run_copy as copies
import bmad_suite_source as source
from bmad_supervisor import SupervisorError


class RunCopyGuards(unittest.TestCase):
    setUpSource = fixtures.SuiteSourceGuards.setUp
    record = staticmethod(fixtures.SuiteSourceGuards.record)
    put = fixtures.SuiteSourceGuards.put
    save_manifests = fixtures.SuiteSourceGuards.save_manifests
    snapshot = fixtures.SuiteSourceGuards.snapshot
    assert_writer_available = fixtures.SuiteSourceGuards.assert_writer_available

    def setUp(self):
        self.setUpSource()
        self.workspace = self.base / "authorized workspace"
        self.workspace.mkdir()
        for path in sorted((SUITE / "scripts").glob("*.py")):
            relative = "scripts/" + path.name
            payload = path.read_bytes()
            self.put(source.PLUGIN + "/" + relative, payload)
            self.sources[relative] = self.record(payload)
            self.files[source.PLUGIN + "/" + relative] = self.record(payload)
        self.save_manifests()

    def prepare(self):
        with source.bound_suite(self.root) as binding:
            return copies.prepare_run_copy(workspace=self.workspace, binding=binding)

    def test_prepare_only_creates_candidate_and_preserves_deployment(self):
        before = self.snapshot()
        with source.bound_suite(self.root) as binding:
            candidate = copies.prepare_run_copy(workspace=self.workspace, binding=binding)
            candidate.check()
            with self.lock.open("rb") as stream:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertEqual(self.snapshot(), before)
        self.assert_writer_available()
        self.assertFalse(candidate.data["agent_started"])
        self.assertFalse(candidate.data["activation_authorized"])
        self.assertEqual(candidate.data["source_commit"], "a" * 40)
        self.assertTrue(candidate.suite_root.is_relative_to(self.workspace))
        self.assertEqual(candidate.entrypoint.read_bytes(), (self.plugin / "scripts/bmad-loop.py").read_bytes())
        self.assertFalse((self.workspace / ".bmad-control/loop-current.json").exists())

    def test_candidate_source_edit_does_not_hot_replace_copy(self):
        candidate = self.prepare()
        original = candidate.entrypoint.read_bytes()
        path = self.plugin / "scripts/bmad-loop.py"
        changed = path.read_bytes() + b"\n# external source edit preserved\n"
        path.write_bytes(changed)
        candidate.check()
        self.assertEqual(candidate.entrypoint.read_bytes(), original)
        with self.assertRaisesRegex(SupervisorError, "摘要不一致"):
            with source.bound_suite(self.root):
                self.fail("变更来源不可重新采用")
        self.assertEqual(path.read_bytes(), changed)

    def test_running_program_must_be_from_exact_bound_copy(self):
        candidate = self.prepare()
        candidate.require_current_program(candidate.suite_root / "scripts")
        with self.assertRaisesRegex(SupervisorError, "当前程序不是绑定运行副本"):
            candidate.require_current_program(SUITE / "scripts")
        other = self.prepare()
        with self.assertRaisesRegex(SupervisorError, "当前程序不是绑定运行副本"):
            candidate.require_current_program(other.suite_root / "scripts")
        candidate.check()
        other.check()

    def test_copy_edit_blocks_without_restoring_user_changes(self):
        candidate = self.prepare()
        changed = candidate.entrypoint.read_bytes() + b"\n# changed bound runtime\n"
        candidate.entrypoint.write_bytes(changed)
        with self.assertRaisesRegex(SupervisorError, "禁止热替换"):
            candidate.check()
        self.assertEqual(candidate.entrypoint.read_bytes(), changed)
        self.assertNotEqual((self.plugin / "scripts/bmad-loop.py").read_bytes(), changed)

    def test_extra_file_symlink_and_hardlink_fail_closed(self):
        candidate = self.prepare()
        extra = candidate.suite_root / "personal.txt"
        extra.write_bytes(b"keep extra\n")
        with self.assertRaisesRegex(SupervisorError, "文件集合变化"):
            candidate.check()
        self.assertEqual(extra.read_bytes(), b"keep extra\n")
        extra.unlink()
        path = candidate.entrypoint
        payload = path.read_bytes()
        path.unlink()
        path.symlink_to(self.plugin / "scripts/bmad-loop.py")
        with self.assertRaisesRegex(SupervisorError, "软链接"):
            candidate.check()
        path.unlink()
        os.link(self.plugin / "scripts/bmad-loop.py", path)
        with self.assertRaisesRegex(SupervisorError, "单硬链接"):
            candidate.check()
        path.unlink()
        path.write_bytes(payload)
        path.chmod(0o600)
        candidate.check()

    def test_missing_runtime_is_not_filled_from_other_version(self):
        relative = "scripts/bmad_loop.py"
        (self.plugin / relative).unlink()
        del self.sources[relative]
        del self.files[source.PLUGIN + "/" + relative]
        self.save_manifests()
        with source.bound_suite(self.root) as binding:
            with self.assertRaisesRegex(SupervisorError, "缺少自包含循环资产"):
                copies.prepare_run_copy(workspace=self.workspace, binding=binding)
        self.assertFalse((self.workspace / copies.PREFIX).exists())
        self.assert_writer_available()

    def test_changed_binding_receipt_and_activation_declaration_block(self):
        candidate = self.prepare()
        path = self.workspace / candidate.receipt_file
        data = dict(candidate.data, activation_authorized=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(SupervisorError, "绑定回执变化"):
            candidate.check()
        with self.assertRaisesRegex(SupervisorError, "激活边界"):
            copies.load_run_copy(workspace=self.workspace, receipt_file=candidate.receipt_file)
        self.assertTrue(json.loads(path.read_bytes())["activation_authorized"])

    def test_source_change_during_copy_preserves_partial_candidate_without_binding(self):
        original = source.read_asset
        changed = False

        def changing(root, relative, budget):
            nonlocal changed
            result = original(root, relative, budget)
            if root == self.plugin and not changed:
                changed = True
                path = self.plugin / "scripts/bmad_loop.py"
                path.write_bytes(path.read_bytes() + b"\n# change during copying\n")
            return result

        # 让复制失败穿过来源租约，验证原始失败传播；不得恢复来源来规避
        # 退出边界的物理身份核验。外部修改及未绑定的部分副本均须保留。
        with self.assertRaisesRegex(SupervisorError, "复制期间绑定来源变化"):
            with source.bound_suite(self.root) as binding:
                with patch.object(source, "read_asset", side_effect=changing):
                    copies.prepare_run_copy(workspace=self.workspace, binding=binding)
        self.assertTrue(changed)
        self.assertEqual(
            (self.plugin / "scripts/bmad_loop.py").read_bytes(),
            (SUITE / "scripts/bmad_loop.py").read_bytes() + b"\n# change during copying\n")
        instances = list((self.workspace / copies.PREFIX).iterdir())
        self.assertEqual(len(instances), 1)
        self.assertFalse((instances[0] / "binding.json").exists())
        self.assertTrue((instances[0] / "suite").is_dir())
        self.assert_writer_available()

    def test_candidate_matches_current_source_binding_without_writes_or_activation(self):
        before = self.snapshot()
        with source.bound_suite(self.root) as binding:
            candidate = copies.prepare_run_copy(workspace=self.workspace, binding=binding)
            candidate.require_source(binding)
            with self.lock.open("rb") as stream:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(candidate.data["agent_started"])
        self.assertFalse(candidate.data["activation_authorized"])
        self.assertFalse((self.workspace / ".bmad-control/loop-current.json").exists())
        self.assert_writer_available()

    def test_stale_candidate_rejects_consistently_updated_source_commit(self):
        candidate = self.prepare()
        original = candidate.entrypoint.read_bytes()
        self.provenance["source_commit"] = "b" * 40
        self.save_manifests()
        before = self.snapshot()
        with source.bound_suite(self.root) as binding:
            with self.assertRaisesRegex(SupervisorError, "当前来源绑定不一致"):
                candidate.require_source(binding)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(candidate.data["source_commit"], "a" * 40)
        self.assertEqual(candidate.entrypoint.read_bytes(), original)
        candidate.check()
        self.assert_writer_available()

    def test_same_commit_with_consistently_updated_assets_rejects_old_candidate(self):
        candidate = self.prepare()
        relative = "scripts/bmad_loop.py"
        original = (candidate.suite_root / relative).read_bytes()
        changed = original + b"\n# authorized candidate source change\n"
        self.put(source.PLUGIN + "/" + relative, changed)
        self.sources[relative] = self.record(changed)
        self.files[source.PLUGIN + "/" + relative] = self.record(changed)
        self.save_manifests()
        before = self.snapshot()
        with source.bound_suite(self.root) as binding:
            self.assertEqual(binding._snapshot["source_commit"], candidate.data["source_commit"])
            with self.assertRaisesRegex(SupervisorError, "当前来源绑定不一致"):
                candidate.require_source(binding)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.plugin / relative).read_bytes(), changed)
        self.assertEqual((candidate.suite_root / relative).read_bytes(), original)
        candidate.check()
        self.assert_writer_available()

    def test_copy_module_is_self_contained_in_isolated_python(self):
        candidate = self.prepare()
        program = (
            "import pathlib, sys; sys.path.insert(0, sys.argv[1]); "
            "import bmad_run_copy as c; "
            "copy=c.load_run_copy(workspace=pathlib.Path(sys.argv[2]), receipt_file=sys.argv[3]); "
            "copy.require_current_program(pathlib.Path(sys.argv[1])); "
            "assert not copy.data['agent_started']; print('COPY_CHECK_ONLY')"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", program, str(candidate.suite_root / "scripts"),
             str(self.workspace), candidate.receipt_file],
            cwd=self.workspace, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "COPY_CHECK_ONLY")
        candidate.check()
        self.assertFalse((self.workspace / ".bmad-control/loop-current.json").exists())


if __name__ == "__main__":
    unittest.main()
