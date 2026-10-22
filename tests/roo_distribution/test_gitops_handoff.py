"""更新执行移交回归；仅使用项目内独立仓库和本地文件远端，无网络或真实推送。"""
import json
import shutil
import unittest

import test_gitops_dry_run as fixtures


class GitOpsHandoff(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree

    def prepare_update(self):
        self.git("checkout", "-b", "fixture-new-entry")
        script = self.repo / "bs.sh"
        source = script.read_text()
        source = source.replace('main "$@"', 'printf "%s\\n" "NEW_ENTRY_LOADED"\nmain "$@"')
        # 明显改变长度；旧 Bash 不可依赖被替换文件的继续读取偏移。
        source = source.replace('# Define colors for output', '# 新版入口夹具\n' * 200)
        script.write_text(source)
        rule = self.repo / "bmad-suite-v4/roo/rules/02-bmad-core.md"
        updated = rule.read_bytes() + b"\n<!-- new entry fixture -->\n"
        rule.write_bytes(updated)
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "-m", "new entry fixture")
        commit = self.git("rev-parse", "HEAD").strip()
        remote = self.sandbox / "local remote.git"
        # 直接从夹具新分支创建文件远端；无需执行任何 push。
        self.git("clone", "--bare", "--branch", "fixture-new-entry", str(self.repo), str(remote))
        self.git("--git-dir", str(remote), "symbolic-ref", "refs/heads/main", "refs/heads/fixture-new-entry")
        self.git("checkout", "main")
        self.git("remote", "add", "origin", str(remote))
        return commit, updated

    def track_git(self):
        real_git = shutil.which("git", path=self.env.get("PATH"))
        self.assertIsNotNone(real_git)
        wrappers = self.sandbox / "command wrappers"
        wrappers.mkdir()
        log = self.sandbox / "git calls.jsonl"
        wrapper = wrappers / "git"
        wrapper.write_text(
            '#!/usr/bin/env python3\nimport json, os, sys\n'
            f'with open({str(log)!r}, "a") as out: out.write(json.dumps(sys.argv[1:]) + "\\n")\n'
            f'os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])\n'
        )
        wrapper.chmod(0o700)
        self.env["PATH"] = str(wrappers) + ":" + self.env["PATH"]
        return log

    def test_update_loads_new_entry_once_preserving_explicit_space_paths(self):
        commit, updated = self.prepare_update()
        log = self.track_git()
        first = ".config/Antigravity IDE/User/globalStorage/rooveterinaryinc.roo-cline/settings/custom_modes.yaml"
        second = "personal profile with 'quote'/settings/custom_modes.yaml"
        for relative in (first, second):
            path = self.target / relative
            path.parent.mkdir(parents=True)
            path.write_bytes(b"theme: dark\ncustomModes: [{slug: personal, name: Personal}]\n")
        # 显式覆盖须贯穿移交；未选中损坏目标不应阻塞。
        ignored = self.target / ".vscode-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings/custom_modes.yaml"
        ignored.parent.mkdir(parents=True)
        ignored.write_bytes(b"customModes: [")
        result = self.run_command([
            "bash", "bs.sh", "--update", "--latest", "v4",
            "--mode-target", first, "--mode-target", second,
        ])
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stdout.count("NEW_ENTRY_LOADED"), 1)
        self.assertEqual(result.stdout.count("显式移交磁盘新版部署入口"), 1)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(sum("fetch" in call for call in calls), 1)
        self.assertEqual(sum("merge" in call for call in calls), 1)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), commit)
        self.assertEqual((self.target / ".roo/rules/02-bmad-core.md").read_bytes(), updated)
        for relative in (first, second):
            self.assertIn(b"personal", (self.target / relative).read_bytes())
            self.assertIn(b"bmad-engineer", (self.target / relative).read_bytes())
        self.assertEqual(ignored.read_bytes(), b"customModes: [")
        self.assertEqual(list(self.home.iterdir()), [])

    def test_latest_switch_hands_off_new_entry_once(self):
        self.prepare_update()
        self.git("checkout", "--detach", "fixture-release")
        self.git("branch", "-f", "main", "fixture-new-entry")
        result = self.run_command(["bash", "bs.sh", "--latest"])
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stdout.count("NEW_ENTRY_LOADED"), 1)
        self.assertEqual(result.stdout.count("显式移交磁盘新版部署入口"), 1)
        self.assertEqual(self.git("branch", "--show-current").strip(), "main")

    def test_new_entry_failure_propagates_without_repeat_or_asset_writes(self):
        self.prepare_update()
        self.git("checkout", "fixture-new-entry")
        script = self.repo / "bs.sh"
        source = script.read_text()
        self.assertIn('main "$@"', source)
        script.write_text(source.replace('main "$@"', 'exit 17\nmain "$@"'))
        self.git("add", "bs.sh")
        self.git("-c", "commit.gpgsign=false", "commit", "-m", "fixture failing entry")
        remote = self.sandbox / "local remote.git"
        # 本地文件远端夹具直接获取新提交；不访问网络或执行 push。
        self.git("--git-dir", str(remote), "fetch", str(self.repo),
                 "fixture-new-entry:refs/heads/fixture-new-entry")
        self.git("checkout", "main")
        before = self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "--update", "v4"])
        self.assertEqual(result.returncode, 17, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("NEW_ENTRY_LOADED"), 1)
        self.assertEqual(result.stdout.count("显式移交磁盘新版部署入口"), 1)
        self.assertEqual(self.tree(self.target), before)

    def test_unknown_deployment_blocks_before_git_or_handoff_even_explicit_v4(self):
        self.prepare_update()
        old = self.target / ".gemini/config/plugins/bmad-suite/plugin.json"
        old.parent.mkdir(parents=True)
        old.write_bytes(b"old unmanaged mirror")
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "--update", "v4"])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("NEW_ENTRY_LOADED", result.stdout)
        self.assertNotIn("显式移交磁盘新版部署入口", result.stdout)
        self.assertIn("所有权清单", result.stderr)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)

    def test_invalid_resume_or_loop_marker_rejected_without_changes(self):
        commit = self.git("rev-parse", "HEAD").strip()
        for arguments, marker in (
            (("--_resume-main", commit), None),
            (("--_resume-main", "0" * 40), "1"),
            (("--_resume-main", commit, "--update"), "1"),
            (("--update",), "1"),
        ):
            with self.subTest(arguments=arguments):
                if marker is None:
                    self.env.pop("BMAD_HANDOFF_ACTIVE", None)
                else:
                    self.env["BMAD_HANDOFF_ACTIVE"] = marker
                before_repo, before_target = self.tree(self.repo), self.tree(self.target)
                result = self.run_command(["bash", "bs.sh", *arguments])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.tree(self.repo), before_repo)
                self.assertEqual(self.tree(self.target), before_target)


if __name__ == "__main__":
    unittest.main()
