"""标签缓存隔离回归：标签移动不能复用旧提交，不完整缓存不能部署。"""
import runpy
import sys
import unittest
from unittest import mock

import test_gitops_dry_run as fixtures


class GitOpsTagCache(fixtures.GitOpsDryRun):
    def test_moved_tag_deploys_new_commit_not_stale_cache(self):
        first = self.run_command(["bash", "bs.sh", "--tag", "fixture-release"])
        self.assertEqual(first.returncode, 0, first.stderr)
        rule = self.repo / "bmad-suite-v4/roo/rules/02-bmad-core.md"
        updated = rule.read_bytes() + b"\n<!-- moved tag fixture -->\n"
        rule.write_bytes(updated)
        self.git("add", "bmad-suite-v4/roo/rules/02-bmad-core.md")
        self.git("-c", "commit.gpgsign=false", "commit", "-m", "new release content")
        self.git("tag", "-f", "fixture-release")
        second = self.run_command(["bash", "bs.sh", "--tag", "fixture-release"])
        self.assertEqual(second.returncode, 0, second.stderr)
        deployed = self.target / ".roo/rules/02-bmad-core.md"
        self.assertEqual(deployed.read_bytes(), updated,
                         "标签移动后不能继续部署旧缓存内容")

    def test_incomplete_legacy_cache_never_changes_deployment(self):
        cache = self.repo / ".versions/fixture-release"
        cache.mkdir(parents=True)
        marker = cache / "partial-extraction.txt"
        marker.write_bytes(b"incomplete legacy cache\n")
        before_target = self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "--tag", "fixture-release"])
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.tree(self.target), before_target,
                         "不完整缓存必须在部署写入前被拒绝")
        self.assertEqual(marker.read_bytes(), b"incomplete legacy cache\n",
                         "拒绝缓存时不得破坏已有诊断证据")


    def test_modified_commit_cache_rejected_without_deployment_changes(self):
        first = self.run_command(["bash", "bs.sh", "--tag", "fixture-release"])
        self.assertEqual(first.returncode, 0, first.stderr)
        commit = self.git("rev-parse", "fixture-release^{commit}").strip()
        cache = self.repo / ".versions" / ("commit-" + commit)
        rule = cache / "bmad-suite-v4/roo/rules/02-bmad-core.md"
        rule.write_bytes(b"modified cached rule\n")
        before_cache = self.tree(cache)
        before_target = self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "--tag", "fixture-release"])
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("缓存内容或权限与实际提交不符", result.stderr)
        self.assertEqual(self.tree(cache), before_cache)
        self.assertEqual(self.tree(self.target), before_target)

    def test_missing_commit_marker_rejected_without_repair(self):
        first = self.run_command(["bash", "bs.sh", "--tag", "fixture-release"])
        self.assertEqual(first.returncode, 0, first.stderr)
        commit = self.git("rev-parse", "fixture-release^{commit}").strip()
        cache = self.repo / ".versions" / ("commit-" + commit)
        marker = cache / "commit.txt"
        marker.unlink()
        before_cache = self.tree(cache)
        before_target = self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "--tag", "fixture-release"])
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("缓存提交标识缺失或不匹配", result.stderr)
        self.assertEqual(self.tree(cache), before_cache)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertFalse(marker.exists())

    def test_symlink_cache_root_rejected_without_touching_destination(self):
        outside_cache = self.sandbox / "other-cache"
        outside_cache.mkdir()
        marker = outside_cache / "personal.txt"
        marker.write_bytes(b"preserve unrelated files\n")
        link = self.repo / ".versions"
        link.symlink_to(outside_cache, target_is_directory=True)
        before_cache = self.tree(outside_cache)
        before_target = self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "--tag", "fixture-release"])
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("拒绝符号链接", result.stderr)
        self.assertTrue(link.is_symlink())
        self.assertEqual(self.tree(outside_cache), before_cache)
        self.assertEqual(self.tree(self.target), before_target)


    def test_publish_failure_leaves_no_completed_cache_and_allows_retry(self):
        scripts = self.repo / "scripts"
        with mock.patch.object(sys, "path", [str(scripts), *sys.path]):
            module = runpy.run_path(str(scripts / "tag-cache.py"))
        commit = self.git("rev-parse", "fixture-release^{commit}").strip()
        cache_root = self.repo / ".versions"
        destination = cache_root / ("commit-" + commit)
        before_target = self.tree(self.target)
        # 注入实际发布步骤故障，保留真实提取、校验和异常清理路径。
        with mock.patch.object(
            module["Path"], "rename", side_effect=OSError("模拟缓存发布失败")
        ) as rename:
            with self.assertRaisesRegex(OSError, "模拟缓存发布失败"):
                module["prepare_cache"](self.repo, "fixture-release")
        rename.assert_called_once_with(destination)
        self.assertFalse(destination.exists())
        self.assertEqual(list(cache_root.glob(".preparing-*")), [])
        self.assertEqual(self.tree(self.target), before_target)
        # 故障后锁应释放，下一次真实入口应能重新构建并部署。
        retried = self.run_command(["bash", "bs.sh", "--tag", "fixture-release"])
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual((destination / "commit.txt").read_text(), commit + "\n")
        source = self.repo / "bmad-suite-v4/roo/rules/02-bmad-core.md"
        deployed = self.target / ".roo/rules/02-bmad-core.md"
        self.assertEqual(deployed.read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()
