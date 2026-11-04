"""标签查询的限时、无副作用及失败传播回归；不联网或部署真实宿主。"""
import os
from pathlib import Path
import shlex
import shutil
import unittest

import test_gitops_dry_run as fixtures


class GitOpsTags(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree

    def wrapper(self, name, content):
        directory = self.sandbox / "command-wrappers"
        directory.mkdir(exist_ok=True)
        path = directory / name
        path.write_text("#!/bin/bash\n" + content, encoding="utf-8")
        path.chmod(0o700)
        self.env["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")

    def query_unchanged(self, option="--tags"):
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        result = self.run_command(["/bin/bash", "bs.sh", option])
        self.assertEqual(self.tree(self.repo), before_repo,
                         "只读标签查询改变了仓库或 Git 元数据")
        self.assertEqual(self.tree(self.target), before_target,
                         "只读标签查询改变了部署资产")
        return result

    def assert_query_failed(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("标签只读查询完成", result.stdout)
        self.assertNotIn("Inspect/deploy a reviewed V4 tag", result.stdout)

    def test_all_aliases_list_local_tags_without_writes(self):
        for option in ("--tags", "-l", "--list-tags"):
            with self.subTest(option=option):
                result = self.query_unchanged(option)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("fixture-release", result.stdout)
                self.assertIn("标签只读查询完成", result.stdout)
                self.assertIn("两段版本", result.stdout)

    def test_missing_repository_fails_without_success_notice_or_writes(self):
        # 构造受控父仓库，防止夹具缺少 .git 时发现真实工作区并读取其标签。
        for arguments in (
            ("init", "--initial-branch=main"),
            ("-c", "commit.gpgsign=false", "commit", "--allow-empty",
             "-m", "fixture parent repository"),
            ("tag", "parent-tag-must-not-be-listed"),
        ):
            prepared = self.run_command([
                "git", "--no-pager", "-C", str(self.sandbox), *arguments,
            ])
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        shutil.rmtree(self.repo / ".git")
        parent_before = self.tree(self.sandbox / ".git")
        result = self.query_unchanged()
        self.assert_query_failed(result)
        self.assertIn("仓库探测失败或超时", result.stderr)
        self.assertIn("实际仓库根目录与部署入口不一致", result.stderr)
        self.assertNotIn("parent-tag-must-not-be-listed", result.stdout)
        self.assertEqual(self.tree(self.sandbox / ".git"), parent_before)

    def test_git_tag_failure_propagates_without_writes(self):
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        self.wrapper("git", "if [[ \" $* \" == *\" tag \"* ]]; then\n"
                     "    printf '%s\\n' 'injected tag failure' >&2\n"
                     "    exit 41\nfi\nexec " + shlex.quote(real_git) + " \"$@\"\n")
        result = self.query_unchanged()
        self.assert_query_failed(result)
        self.assertEqual(result.returncode, 41)
        self.assertIn("injected tag failure", result.stderr)

    def test_tag_timeout_result_propagates_without_writes(self):
        real_timeout = shutil.which("timeout")
        self.assertIsNotNone(real_timeout)
        self.wrapper("timeout", "if [[ \" $* \" == *\" tag \"* ]]; then\n"
                     "    printf '%s\\n' 'injected tag timeout' >&2\n"
                     "    exit 124\nfi\nexec " + shlex.quote(real_timeout) + " \"$@\"\n")
        result = self.query_unchanged()
        self.assert_query_failed(result)
        self.assertEqual(result.returncode, 124)
        self.assertIn("injected tag timeout", result.stderr)

    def test_timeout_probe_failure_propagates_without_writes(self):
        self.wrapper("timeout", "printf '%s\\n' 'injected timeout probe failure' >&2\nexit 42\n")
        result = self.query_unchanged()
        self.assert_query_failed(result)
        self.assertEqual(result.returncode, 42)

    def test_non_gnu_timeout_is_rejected_without_writes(self):
        self.wrapper("timeout", "printf '%s\\n' 'unsupported timeout implementation'\n")
        result = self.query_unchanged()
        self.assert_query_failed(result)
        self.assertIn("需要 GNU timeout", result.stderr)

    def test_missing_query_dependencies_fail_without_writes(self):
        for missing in ("git", "timeout", "env"):
            with self.subTest(missing=missing):
                directory = self.sandbox / ("missing-" + missing)
                directory.mkdir()
                for command in ("dirname", "git", "timeout", "env"):
                    if command != missing:
                        executable = shutil.which(command)
                        self.assertIsNotNone(executable)
                        (directory / command).symlink_to(Path(executable))
                self.env["PATH"] = str(directory)
                result = self.query_unchanged()
                self.assert_query_failed(result)
                self.assertIn("缺少标签查询依赖 " + missing, result.stderr)


if __name__ == "__main__":
    unittest.main()
