"""V5 来源绑定反例：合成分发夹具，不启动 Agent 或访问来源仓库。

实际公共部署产物的兼容性另由工程分发测试验证；本文件只核验来源
绑定、文件身份、协作租约与失败关闭，不证明宿主模式或运行时加载。
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_suite_source as source
from bmad_supervisor import SupervisorError


class SuiteSourceGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-suite-source-", dir=SUITE.parent / "tests",
        )
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "deployment with 'quote'"
        self.root.mkdir()
        self.plugin = self.root / source.PLUGIN
        self.lock = self.root / ".bmad-solo-deployment/deployment.lock"
        self.lock.parent.mkdir()
        self.lock.write_bytes(b"existing lock\n")
        self.lock.chmod(0o600)
        self.personal = self.root / "personal.txt"
        self.personal.write_bytes(b"preserve unrelated user changes\n")
        self.sources = {}
        for relative in sorted(source.REQUIRED):
            content = ("fixture asset: " + relative + "\n").encode()
            if relative == "plugin.json":
                content = json.dumps({"name": "bmad-suite",
                                      "displayName": "BMRalph V5"}).encode()
            elif relative == "suite.json":
                content = json.dumps(source.IDENTITY).encode()
            self.sources[relative] = self.record(content)
            self.put(source.PLUGIN + "/" + relative, content)
            if relative in {"rules/bmad-constitution.md", "rules/bmad-core.md"}:
                self.put(".gemini/config/" + relative, content)
            if any(relative.startswith("roo/" + section + "/") for section in (
                    "rules", "rules-ana-architect", "rules-bmad-engineer")):
                self.put(".roo/" + relative.removeprefix("roo/"), content)
        self.files = {path.relative_to(self.root).as_posix(): self.record(path.read_bytes())
                      for path in self.root.rglob("*")
                      if path.is_file() and path not in {self.personal, self.lock}}
        self.provenance = {
            "schema_version": 1,
            "suite_id": "bmralph-suite-v5", "major_version": "v5",
            "source_path": "bmralph-suite-v5",
            "source_directory": str(self.base / "unavailable repo/bmralph-suite-v5"),
            "source_repository": str(self.base / "unavailable repo"),
            "source_commit": "a" * 40, "source_kind": "worktree",
            "source_dirty": True, "source_files": self.sources,
            "managed_files": self.files, "managed_modes": {},
        }
        self.ownership = {"schema_version": 1, "files": {}, "modes": {}}
        self.save_manifests()

    @staticmethod
    def record(content, mode=0o600):
        return {"sha256": hashlib.sha256(content).hexdigest(), "mode": mode}

    def put(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(0o600)
        return path

    def save_manifests(self):
        content = json.dumps(self.provenance, sort_keys=True).encode()
        self.put(source.PROVENANCE, content)
        self.ownership["files"] = dict(self.files)
        self.ownership["files"][source.PROVENANCE] = self.record(content)
        self.put(source.OWNERSHIP, json.dumps(self.ownership, sort_keys=True).encode())

    def snapshot(self):
        return {path.relative_to(self.root).as_posix():
                (path.read_bytes(), path.stat().st_mode, path.stat().st_ino)
                for path in self.root.rglob("*") if path.is_file() and not path.is_symlink()}

    def assert_writer_available(self):
        with self.lock.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def assert_blocked(self, pattern=None):
        before = self.snapshot()
        context = (self.assertRaisesRegex((SupervisorError, OSError), pattern)
                   if pattern else self.assertRaises((SupervisorError, OSError)))
        with context:
            with source.bound_suite(self.root):
                self.fail("非法来源不得进入任务")
        self.assertEqual(self.snapshot(), before)
        if self.lock.exists():
            self.assert_writer_available()

    def test_valid_binding_is_read_only_without_accessing_source_repository(self):
        before = self.snapshot()
        self.assertFalse(Path(self.provenance["source_repository"]).exists())
        with source.bound_suite(self.root) as binding:
            self.assertEqual(binding.suite_root, self.plugin)
            binding.check()
            with self.lock.open("rb") as stream:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertEqual(self.snapshot(), before)
        self.assert_writer_available()

    def test_missing_lock_is_not_recreated(self):
        self.lock.unlink()
        self.assert_blocked()
        self.assertFalse(self.lock.exists())

    def test_exclusive_deployment_blocks_binding(self):
        with self.lock.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(SupervisorError, "部署正在进行"):
                with source.bound_suite(self.root):
                    self.fail("不得在部署期间绑定")
        self.assert_writer_available()

    def test_missing_provenance_is_not_synthesized(self):
        (self.root / source.PROVENANCE).unlink()
        self.assert_blocked()
        self.assertFalse((self.root / source.PROVENANCE).exists())

    def test_modified_distributed_asset_blocks_without_restoring(self):
        path = self.plugin / "scripts/bmad-exec.py"
        path.write_bytes(b"external user change\n")
        self.assert_blocked("摘要不一致")
        self.assertEqual(path.read_bytes(), b"external user change\n")

    def test_modified_mirrored_rule_blocks(self):
        self.put(".roo/rules/02-bmad-core.md", b"external mirrored rule\n")
        self.assert_blocked("摘要不一致")

    def test_extra_plugin_file_blocks_without_deleting_user_asset(self):
        extra = self.put(source.PLUGIN + "/personal.txt", b"keep plugin extra\n")
        self.assert_blocked("物理文件集合")
        self.assertEqual(extra.read_bytes(), b"keep plugin extra\n")

    def test_omitted_required_asset_blocks_even_with_consistent_manifests(self):
        relative = "scripts/bmad-exec.py"
        (self.plugin / relative).unlink()
        del self.sources[relative]
        del self.files[source.PLUGIN + "/" + relative]
        self.save_manifests()
        self.assert_blocked("必需运行资产")

    def test_other_version_and_unknown_version_are_not_adopted(self):
        for version in ("v4", None):
            with self.subTest(version=version):
                self.provenance["major_version"] = version
                self.save_manifests()
                self.assert_blocked("明确为 V5")

    def test_invalid_commit_kind_or_dirty_state_blocks(self):
        original = dict(self.provenance)
        for changes in ({"source_commit": "not-a-commit"},
                        {"source_kind": "unversioned"},
                        {"source_dirty": 1},
                        {"source_kind": "commit_cache", "source_dirty": True},
                        {"source_repository": "relative/repo"},
                        {"source_directory": str(self.base / "other-suite")}):
            with self.subTest(changes=changes):
                self.provenance = dict(original, **changes)
                self.save_manifests()
                self.assert_blocked("版本记录")

    def test_valid_commit_cache_can_bind(self):
        self.provenance.update(source_kind="commit_cache", source_dirty=False)
        self.save_manifests()
        with source.bound_suite(self.root) as binding:
            binding.check()

    def test_identity_file_mismatch_blocks_even_with_updated_digests(self):
        relative = "suite.json"
        content = json.dumps(dict(source.IDENTITY, suite_id="wrong-suite")).encode()
        self.put(source.PLUGIN + "/" + relative, content)
        self.sources[relative] = self.record(content)
        self.files[source.PLUGIN + "/" + relative] = self.record(content)
        self.save_manifests()
        self.assert_blocked("身份资产")

    def test_duplicate_json_keys_block(self):
        self.put(source.OWNERSHIP, b'{"schema_version":1,"schema_version":1}')
        self.assert_blocked("重复字段")

    def test_path_escape_and_invalid_records_block(self):
        for key, value in (("../escape", self.record(b"x")),
                           ("valid/path", {"sha256": "invalid", "mode": 0o600}),
                           ("valid/path", {"sha256": "a" * 64, "mode": True})):
            with self.subTest(key=key, value=value):
                original = dict(self.ownership["files"])
                self.ownership["files"][key] = value
                self.put(source.OWNERSHIP, json.dumps(self.ownership).encode())
                self.assert_blocked()
                self.ownership["files"] = original

    def test_inconsistent_mapping_blocks(self):
        del self.files[".roo/rules/02-bmad-core.md"]
        self.save_manifests()
        self.assert_blocked("分发映射")

    def test_hardlink_symlink_and_fifo_block_without_modifying_destination(self):
        path = self.plugin / "scripts/bmad-exec.py"
        original = path.read_bytes()
        path.unlink()
        os.link(self.personal, path)
        self.assert_blocked("单硬链接")
        path.unlink()
        path.symlink_to(self.personal)
        self.assert_blocked()
        path.unlink()
        os.mkfifo(path)
        self.assert_blocked("物理文件")
        path.unlink()
        self.put(source.PLUGIN + "/scripts/bmad-exec.py", original)
        self.assertEqual(self.personal.read_bytes(), b"preserve unrelated user changes\n")

    def test_ancestor_symlink_is_rejected(self):
        alias = self.base / "alias"
        alias.symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaises(SupervisorError):
            with source.bound_suite(alias / self.root.name):
                self.fail("不得通过父目录链接绑定")
        self.assert_writer_available()

    def test_file_budget_is_enforced(self):
        with mock.patch.object(source, "MAX_FILE_BYTES", 16):
            self.assert_blocked("单文件读取预算")
        with mock.patch.object(source, "MAX_TOTAL_BYTES", 16):
            self.assert_blocked("读取超出预算")

    def test_change_during_capture_blocks(self):
        original = source.read_asset
        changed = False
        def changing(root, relative, budget):
            nonlocal changed
            result = original(root, relative, budget)
            if relative == source.PLUGIN + "/plugin.json" and not changed:
                changed = True
                (self.root / source.OWNERSHIP).write_bytes(b"external replacement\n")
            return result
        with mock.patch.object(source, "read_asset", side_effect=changing):
            with self.assertRaises(SupervisorError):
                with source.bound_suite(self.root):
                    self.fail("采集期间变化不得通过")
        self.assertEqual((self.root / source.OWNERSHIP).read_bytes(), b"external replacement\n")
        self.assert_writer_available()

    def test_consistently_rewritten_source_is_rejected_at_boundary(self):
        with self.assertRaisesRegex(SupervisorError, "已绑定套件来源发生变化"):
            with source.bound_suite(self.root):
                self.provenance["source_commit"] = "b" * 40
                self.save_manifests()
        self.assertEqual(self.provenance["source_commit"], "b" * 40)
        self.assert_writer_available()

    def test_original_failure_survives_source_change(self):
        failure = RuntimeError("真实调用方失败")
        with self.assertRaises(RuntimeError) as caught:
            with source.bound_suite(self.root):
                self.put(source.PLUGIN + "/scripts/bmad-exec.py", b"external change\n")
                raise failure
        self.assertIs(caught.exception, failure)
        self.assert_writer_available()

    def test_cancellation_propagates_without_claiming_process_cleanup(self):
        before = self.snapshot()
        with self.assertRaises(KeyboardInterrupt):
            with source.bound_suite(self.root):
                raise KeyboardInterrupt()
        self.assertEqual(self.snapshot(), before)
        self.assert_writer_available()


if __name__ == "__main__":
    unittest.main()
