"""在独立仓库验证版本操作的模拟执行不改变引用、缓存或部署目标。"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class GitOpsDryRun(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-gitops-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.sandbox = Path(self.temp.name)
        self.repo = self.sandbox / "repository"
        self.target = self.sandbox / "deployment"
        self.home = self.sandbox / "home"
        self.repo.mkdir()
        self.target.mkdir()
        self.home.mkdir()
        self.env = dict(os.environ)
        # 不让宿主 Git 环境重定向夹具仓库或加载用户配置。
        for key in list(self.env):
            if key.startswith("GIT_"):
                del self.env[key]
        self.env.update({
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / "config"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            "BMAD_DEPLOY_ROOT": str(self.target),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        shutil.copy2(ROOT / "bs.sh", self.repo / "bs.sh")
        shutil.copytree(ROOT / "scripts", self.repo / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(ROOT / "bmad-suite-v4", self.repo / "bmad-suite-v4")
        self.git("init", "--initial-branch=main")
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "-m", "fixture baseline")
        self.git("tag", "fixture-release")

    def run_command(self, command):
        return subprocess.run(
            command, cwd=self.repo, env=self.env,
            stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=10,
        )

    def git(self, *arguments):
        result = self.run_command(["git", "--no-pager", *arguments])
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def tree(self, root):
        return {
            path.relative_to(root).as_posix():
                ("directory" if path.is_dir() else path.read_bytes(),
                 path.stat().st_mode)
            for path in root.rglob("*")
        }

    def assert_dry_run_unchanged(self, *arguments):
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "--dry-run", *arguments])
        # 先验证无副作用；不能用非零退出掩盖已发生的修改。
        self.assertEqual(self.tree(self.repo), before_repo,
                         "模拟执行改变了仓库、Git 元数据或标签缓存")
        self.assertEqual(self.tree(self.target), before_target,
                         "模拟执行改变了部署目标")
        return result

    def test_tag_dry_run_does_not_create_cache(self):
        result = self.assert_dry_run_unchanged("--tag", "fixture-release")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.repo / ".versions").exists())

    def test_latest_dry_run_does_not_switch_branch(self):
        self.git("checkout", "-b", "fixture-feature")
        result = self.assert_dry_run_unchanged("--latest")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("branch", "--show-current").strip(), "fixture-feature")

    def test_update_dry_run_does_not_require_remote_access(self):
        # 不配置远端：真正的模拟执行不应尝试 fetch 或 pull。
        result = self.assert_dry_run_unchanged("--update")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
