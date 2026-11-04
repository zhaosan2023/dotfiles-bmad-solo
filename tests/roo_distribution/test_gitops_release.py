"""部署提示绑定实际套件版本；仅项目内仓库和部署夹具，不访问网络。"""
import unittest

import test_gitops_dry_run as fixtures


class GitOpsRelease(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree

    def test_current_deployment_reports_declared_release(self):
        declared_bytes = (self.repo / "bmad-suite-v4/VERSION").read_bytes()
        declared = declared_bytes.decode("ascii").strip()
        result = self.run_command(["bash", "bs.sh"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"Bootstrapping BMAD-Solo {declared}", result.stdout)
        self.assertIn(f"{declared} 工程入口", result.stdout)
        self.assertEqual((self.target / ".gemini/config/plugins/bmad-suite/VERSION").read_bytes(),
                         declared_bytes)

    def test_corrupt_declared_release_blocks_before_target_writes(self):
        version = self.repo / "bmad-suite-v4/VERSION"
        for content in (b"v4.3.0\n", b"v4.3", b"", b"v4.03\n"):
            version.write_bytes(content)
            before_repo, before_target = self.tree(self.repo), self.tree(self.target)
            result = self.run_command(["bash", "bs.sh"])
            with self.subTest(content=content):
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.tree(self.repo), before_repo)
                self.assertEqual(self.tree(self.target), before_target)
                self.assertNotIn("受管资产处理完成", result.stdout)

    def test_legacy_source_does_not_claim_current_minor_release(self):
        (self.repo / "bmad-suite-v4/VERSION").unlink()
        result = self.run_command(["bash", "bs.sh"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("旧套件未声明发布小版本", result.stderr)
        self.assertIn("Bootstrapping BMAD-Solo v4", result.stdout)
        self.assertNotIn("v4.3 工程入口", result.stdout)
        self.assertFalse((self.target / ".gemini/config/plugins/bmad-suite/VERSION").exists())

    def test_tag_deployment_reads_snapshot_not_current_version(self):
        (self.repo / "bmad-suite-v4/VERSION").write_bytes(b"v4.2\n")
        self.git("add", "bmad-suite-v4/VERSION")
        self.git("-c", "commit.gpgsign=false", "commit", "-m", "fixture previous release")
        self.git("tag", "v4.2")
        (self.repo / "bmad-suite-v4/VERSION").write_bytes(b"v4.3\n")
        before_source = self.tree(self.repo / "bmad-suite-v4")
        result = self.run_command(["bash", "bs.sh", "--tag", "v4.2"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Bootstrapping BMAD-Solo v4.2", result.stdout)
        self.assertIn("v4.2 工程入口", result.stdout)
        self.assertNotIn("v4.3 工程入口", result.stdout)
        self.assertEqual((self.target / ".gemini/config/plugins/bmad-suite/VERSION").read_bytes(),
                         b"v4.2\n")
        self.assertEqual(self.tree(self.repo / "bmad-suite-v4"), before_source)

    def test_help_shows_two_segment_examples_without_side_effects(self):
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("v4.3、v4.4", result.stdout)
        self.assertNotIn("v4.0.0", result.stdout)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)


if __name__ == "__main__":
    unittest.main()
