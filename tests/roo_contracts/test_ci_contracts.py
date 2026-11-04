"""CI 静态配置回归；不执行网络安装、远程 CI 或真实宿主部署。"""
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]


class CiContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = yaml.safe_load(
            (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        )

    def step(self, job, name):
        matches = [
            step for step in self.config["jobs"][job]["steps"]
            if step.get("name") == name
        ]
        self.assertEqual(len(matches), 1, name)
        return matches[0]

    def test_read_only_repository_permissions(self):
        self.assertEqual(self.config["permissions"], {"contents": "read"})
        for job in self.config["jobs"].values():
            self.assertGreater(job["timeout-minutes"], 0)
            checkouts = [
                step for step in job["steps"]
                if step.get("uses", "").startswith("actions/checkout@")
            ]
            self.assertEqual(len(checkouts), 1)
            self.assertIs(checkouts[0]["with"]["persist-credentials"], False)

    def test_static_gate_selects_only_v4(self):
        script = self.step(
            "lint-and-audit",
            "Validate V4 Configuration and Metadata Contracts",
        )["run"]
        self.assertIn("set -euo pipefail", script)
        self.assertIn(
            "timeout 30s python3 -B scripts/validate-roo-contracts.py "
            "--suite v4 < /dev/null", script,
        )
        self.assertNotIn("--suite v3", script)
        self.assertNotIn("--suite v5", script)

    def test_dependency_preparation_is_separate_from_test_steps(self):
        for name, job in self.config["jobs"].items():
            with self.subTest(job=name):
                steps = job["steps"]
                preparation = [
                    index for index, step in enumerate(steps)
                    if "pip install" in step.get("run", "")
                ]
                self.assertEqual(len(preparation), 1)
                self.assertIn(
                    "timeout 600s python3 -m pip install --no-input",
                    steps[preparation[0]]["run"],
                )
                for index, step in enumerate(steps):
                    script = step.get("run", "")
                    if "unittest" in script or "scripts/run-required-tests.py" in script:
                        self.assertGreater(index, preparation[0])
                        for installer in ("pip install", "apk add", "apt-get install"):
                            self.assertNotIn(installer, script)
                        self.assertRegex(script, r"timeout(?: --kill-after=2s)? 30s")
                        self.assertIn("< /dev/null", script)

    def test_distribution_groups_fail_closed_and_run_serially(self):
        names_and_patterns = (
            ("Test Asset Protection in Bounded Sequential Groups", "test_asset_safety*.py"),
            ("Test GitOps and Three IDE Layouts in Bounded Sequential Groups", "test_gitops*.py"),
            ("Test Suite Selection and Compatibility in Bounded Sequential Groups", "test_suite*.py"),
        )
        for name, pattern in names_and_patterns:
            with self.subTest(step=name):
                step = self.step("test-physical-mirror-install", name)
                self.assertEqual(step["shell"], "bash")
                script = step["run"]
                self.assertIn("set -euo pipefail", script)
                self.assertIn("shopt -s nullglob", script)
                self.assertIn(f"groups=(tests/roo_distribution/{pattern})", script)
                self.assertIn('if [ "${#groups[@]}" -eq 0 ]; then', script)
                self.assertIn("exit 1", script)
                self.assertIn('for group in "${groups[@]}"; do', script)
                self.assertIn("timeout --kill-after=2s 30s python3 -B scripts/run-required-tests.py", script)
                self.assertIn('--directory tests/roo_distribution --pattern "${group##*/}"', script)
                self.assertIn("< /dev/null", script)
                self.assertNotIn("xargs", script)
                self.assertNotIn("parallel", script)
                self.assertNotIn("&\n", script)

    def test_retired_migration_gate_is_explicit_bounded_and_serial(self):
        step = self.step(
            "test-physical-mirror-install", "Test Retired Deployment Migration in Isolation",
        )
        self.assertEqual(step["shell"], "bash")
        script = step["run"]
        self.assertIn("set -euo pipefail", script)
        self.assertIn("test -f tests/roo_distribution/test_retired_deployment_migration.py", script)
        self.assertIn("timeout --kill-after=2s 15s python3 -B -c", script)
        self.assertIn("timeout --kill-after=2s 30s python3 -B -c", script)
        self.assertIn('pattern="test_retired_deployment_migration.py"', script)
        self.assertIn("suite.countTestCases() == 0", script)
        self.assertIn("yield from flatten(item)", script)
        self.assertIn("len(cases) != suite.countTestCases()", script)
        self.assertIn("len(set(cases)) != len(cases)", script)
        self.assertIn('while IFS= read -r case; do', script)
        self.assertIn('done <<< "$cases"', script)
        self.assertIn("suite.countTestCases() != 1", script)
        self.assertIn("result.wasSuccessful() and not result.skipped", script)
        self.assertIn("< /dev/null", script)
        for forbidden in ("xargs", "parallel", "&", "migrate-retired-deployment.py --root"):
            self.assertNotIn(forbidden, script)

    def test_retired_migration_collection_fails_closed(self):
        script = self.step(
            "test-physical-mirror-install", "Test Retired Deployment Migration in Isolation",
        )["run"]
        cases = (
            ("missing", None, False),
            ("empty", "import unittest\n", False),
            ("skipped", "import unittest\nclass Case(unittest.TestCase):\n"
             "    @unittest.skip('required evidence unavailable')\n"
             "    def test_required(self): pass\n", False),
            ("failed", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_required(self): self.fail('injected failure')\n", False),
            ("passed", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_required(self): self.assertTrue(True)\n", True),
            ("multiple", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_first(self): self.assertTrue(True)\n"
             "    def test_second(self): self.assertTrue(True)\n", True),
            ("mixed_skip", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_first(self): self.assertTrue(True)\n"
             "    @unittest.skip('required evidence unavailable')\n"
             "    def test_second(self): pass\n", False),
        )
        for name, content, expected in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory(
                prefix="sandbox-ci-collection-", dir=Path(__file__).parent,
            ) as temporary:
                root = Path(temporary)
                directory = root / "tests/roo_distribution"
                directory.mkdir(parents=True)
                if content is not None:
                    (directory / "test_retired_deployment_migration.py").write_text(
                        content, encoding="utf-8",
                    )
                result = subprocess.run(
                    ["bash", "-c", script], cwd=root, stdin=subprocess.DEVNULL,
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode == 0, expected, result.stdout + result.stderr)
                if name == "empty":
                    self.assertIn("Missing retired deployment migration test cases", result.stderr)
                if expected:
                    self.assertEqual(result.stderr.count("Ran 1 test"),
                                     2 if name == "multiple" else 1)

    def test_new_release_tags_trigger_format_validation(self):
        # PyYAML 的 YAML 1.1 会把未加引号的 on 解析为 True。
        triggers = self.config.get("on", self.config.get(True))
        self.assertEqual(triggers["push"]["branches"], ["main"])
        self.assertEqual(triggers["push"]["tags"], ["v4.*"])
        self.assertEqual(triggers["pull_request"]["branches"], ["main"])
        script = self.step(
            "lint-and-audit", "Validate Two-Segment Release and Source Consistency",
        )["run"]
        for token in ("set -euo pipefail", "args=(--root .)",
                      'args+=(--tag "$GITHUB_REF_NAME")',
                      "timeout --kill-after=2s 30s python3 -B scripts/release_version.py",
                      '"${args[@]}" < /dev/null'):
            self.assertIn(token, script)
        self.assertNotIn("${{", script)

    def test_release_gate_rejects_bad_tags_without_interpreting_shell_content(self):
        script = self.step(
            "lint-and-audit", "Validate Two-Segment Release and Source Consistency",
        )["run"]
        version = (ROOT / "bmad-suite-v4/VERSION").read_text(encoding="ascii").strip()
        import os
        with tempfile.TemporaryDirectory(
            prefix="sandbox-ci-release-", dir=Path(__file__).parent,
        ) as temporary:
            marker = Path(temporary) / "must-not-exist"
            cases = (("branch", "main", True), ("tag", version, True),
                     ("tag", version + ".0", False), ("tag", "v4.999999", False),
                     ("tag", f"v4.3; touch {marker}", False),
                     ("tag", f"$(touch {marker})", False))
            for ref_type, ref_name, expected in cases:
                with self.subTest(ref_type=ref_type, ref_name=ref_name):
                    result = subprocess.run(
                        ["bash", "-c", script], cwd=ROOT, stdin=subprocess.DEVNULL,
                        capture_output=True, text=True, timeout=10,
                        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                             "GITHUB_REF_TYPE": ref_type, "GITHUB_REF_NAME": ref_name},
                    )
                    self.assertEqual(result.returncode == 0, expected,
                                     result.stdout + result.stderr)
                    self.assertFalse(marker.exists())

    def test_release_regression_is_explicit_and_bounded(self):
        script = self.step("lint-and-audit", "Test Release Version Contracts")["run"]
        self.assertIn("timeout --kill-after=2s 30s python3 -B -c", script)
        self.assertIn('pattern="test_release_versions.py"', script)
        self.assertIn("< /dev/null", script)
        self.assertTrue((ROOT / "tests/roo_distribution/test_release_versions.py").is_file())

    def test_install_dependency_regression_is_explicit_and_bounded(self):
        script = self.step(
            "test-physical-mirror-install", "Test Installation Dependency Preflight",
        )["run"]
        self.assertIn("timeout --kill-after=2s 30s python3 -B -c", script)
        self.assertIn('pattern="test_install_dependencies.py"', script)
        self.assertIn("< /dev/null", script)
        self.assertTrue((ROOT / "tests/roo_distribution/test_install_dependencies.py").is_file())
        for forbidden in ("pip install", "apt-get install", "--update", "--latest"):
            self.assertNotIn(forbidden, script)

    def required_regression_steps(self):
        return (
            ("lint-and-audit", "Test Release Version Contracts", "test_release_versions.py"),
            ("test-physical-mirror-install", "Test Installation Dependency Preflight",
             "test_install_dependencies.py"),
            ("test-physical-mirror-install", "Test Deployed Rule Link Contracts",
             "test_deployed_rule_links.py"),
            ("test-physical-mirror-install", "Test Portable Governance Contracts",
             "test_portable_governance.py"),
        )

    def test_required_regressions_are_explicit_bounded_and_fail_closed(self):
        for job, name, pattern in self.required_regression_steps():
            with self.subTest(step=name):
                step = self.step(job, name)
                self.assertEqual(step["shell"], "bash")
                script = step["run"]
                for token in ("set -euo pipefail", f"test -f tests/roo_distribution/{pattern}",
                              "timeout --kill-after=2s 30s python3 -B -c",
                              f'pattern="{pattern}"', "suite.countTestCases() == 0",
                              "result.wasSuccessful() and not result.skipped", "< /dev/null"):
                    self.assertIn(token, script)
                for forbidden in ("pip install", "apt-get install", "--update", "--latest",
                                  "parallel", "xargs", "&"):
                    self.assertNotIn(forbidden, script)

    def test_required_regression_collection_rejects_missing_empty_skipped_and_failed_cases(self):
        cases = (
            ("missing", None, False),
            ("empty", "import unittest\n", False),
            ("skipped", "import unittest\nclass Case(unittest.TestCase):\n"
             "    @unittest.skip('required evidence unavailable')\n"
             "    def test_required(self): pass\n", False),
            ("failed", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_required(self): self.fail('injected failure')\n", False),
            ("passed", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_required(self): self.assertTrue(True)\n", True),
            ("mixed_skip", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_first(self): self.assertTrue(True)\n"
             "    @unittest.skip('required evidence unavailable')\n"
             "    def test_second(self): pass\n", False),
        )
        for job, name, pattern in self.required_regression_steps():
            script = self.step(job, name)["run"]
            for case, content, expected in cases:
                with self.subTest(step=name, case=case), tempfile.TemporaryDirectory(
                    prefix="sandbox-ci-required-", dir=Path(__file__).parent,
                ) as temporary:
                    root = Path(temporary)
                    directory = root / "tests/roo_distribution"
                    directory.mkdir(parents=True)
                    if content is not None:
                        (directory / pattern).write_text(content, encoding="utf-8")
                    result = subprocess.run(
                        ["bash", "-c", script], cwd=root, stdin=subprocess.DEVNULL,
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode == 0, expected,
                                     result.stdout + result.stderr)
                    if case == "empty":
                        self.assertIn("Missing required regression test cases", result.stderr)
                    if expected:
                        self.assertIn("Ran 1 test", result.stderr)

    def test_skill_integrity_gates_use_existing_assets_and_bounded_commands(self):
        validation = self.step(
            "lint-and-audit", "Validate Self-Contained Skill Assets",
        )["run"]
        self.assertIn("timeout --kill-after=2s 30s python3 -B", validation)
        self.assertIn("bmad-suite-v4/skills/bmad/scripts/validate-solo-package.py", validation)
        self.assertIn("< /dev/null", validation)
        self.assertTrue((ROOT / "bmad-suite-v4/skills/bmad/scripts/validate-solo-package.py").is_file())
        step = self.step(
            "test-physical-mirror-install", "Test Skill Integrity and Source Boundaries",
        )
        self.assertEqual(step["shell"], "bash")
        script = step["run"]
        for required in ("set -euo pipefail", "test -f tests/roo_distribution/test_skill_integrity.py",
                         "timeout --kill-after=2s 30s python3 -B -c",
                         'pattern="test_skill_integrity.py"', "suite.countTestCases() == 0",
                         "result.wasSuccessful() and not result.skipped", "< /dev/null"):
            self.assertIn(required, script)
        for forbidden in ("pip install", "apt-get install", "--update", "--latest", "parallel"):
            self.assertNotIn(forbidden, script)

    def test_skill_integrity_collection_rejects_missing_empty_skipped_and_failed_cases(self):
        script = self.step(
            "test-physical-mirror-install", "Test Skill Integrity and Source Boundaries",
        )["run"]
        cases = (
            ("missing", None, False),
            ("empty", "import unittest\n", False),
            ("skipped", "import unittest\nclass Case(unittest.TestCase):\n"
             "    @unittest.skip('required evidence unavailable')\n"
             "    def test_required(self): pass\n", False),
            ("failed", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_required(self): self.fail('injected failure')\n", False),
            ("passed", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_required(self): self.assertTrue(True)\n", True),
            ("mixed_skip", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_first(self): self.assertTrue(True)\n"
             "    @unittest.skip('required evidence unavailable')\n"
             "    def test_second(self): pass\n", False),
        )
        for name, content, expected in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory(
                prefix="sandbox-ci-skills-", dir=Path(__file__).parent,
            ) as temporary:
                root = Path(temporary)
                directory = root / "tests/roo_distribution"
                directory.mkdir(parents=True)
                if content is not None:
                    (directory / "test_skill_integrity.py").write_text(content, encoding="utf-8")
                result = subprocess.run(
                    ["bash", "-c", script], cwd=root, stdin=subprocess.DEVNULL,
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode == 0, expected, result.stdout + result.stderr)
                if name == "empty":
                    self.assertIn("Missing skill integrity test cases", result.stderr)
                if expected:
                    self.assertIn("Ran 1 test", result.stderr)

    def test_cline_regressions_are_explicit_bounded_and_serial(self):
        step = self.step(
            "test-physical-mirror-install",
            "Test Cline Skills and Installation in Bounded Sequential Groups",
        )
        self.assertEqual(step["shell"], "bash")
        script = step["run"]
        groups = ("test_cline_skill_assets.py", "test_cline_distribution.py",
                  "test_cline_installer.py")
        self.assertIn("for group in " + " ".join(groups) + "; do", script)
        for group in groups:
            self.assertTrue((ROOT / "tests/roo_distribution" / group).is_file())
        for required in ("set -euo pipefail", 'test -f "tests/roo_distribution/$group"',
                         "timeout --kill-after=2s 30s python3 -B -c",
                         "pattern=sys.argv[1]", "suite.countTestCases() == 0",
                         "result.wasSuccessful() and not result.skipped",
                         '\' "$group" < /dev/null', "done"):
            self.assertIn(required, script)
        for forbidden in ("pip install", "apt-get install", "parallel", "xargs", "&"):
            self.assertNotIn(forbidden, script)

    def test_cline_collection_rejects_missing_empty_skipped_and_failed_groups(self):
        script = self.step(
            "test-physical-mirror-install",
            "Test Cline Skills and Installation in Bounded Sequential Groups",
        )["run"]
        groups = ("test_cline_skill_assets.py", "test_cline_distribution.py",
                  "test_cline_installer.py")
        passed = ("import unittest\nclass Case(unittest.TestCase):\n"
                  "    def test_required(self): self.assertTrue(True)\n")
        cases = (
            ("missing", None, False),
            ("empty", "import unittest\n", False),
            ("skipped", "import unittest\nclass Case(unittest.TestCase):\n"
             "    @unittest.skip('required evidence unavailable')\n"
             "    def test_required(self): pass\n", False),
            ("failed", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_required(self): self.fail('injected failure')\n", False),
            ("mixed_skip", passed + "    @unittest.skip('required evidence unavailable')\n"
             "    def test_second(self): pass\n", False),
            ("passed", passed, True),
        )
        for selected, group in enumerate(groups):
            for name, content, expected in cases:
                with self.subTest(group=group, case=name), tempfile.TemporaryDirectory(
                    prefix="sandbox-ci-cline-", dir=Path(__file__).parent,
                ) as temporary:
                    root = Path(temporary)
                    directory = root / "tests/roo_distribution"
                    directory.mkdir(parents=True)
                    for candidate in groups:
                        value = content if candidate == group else passed
                        if value is not None:
                            (directory / candidate).write_text(
                                value + f"print('executed {candidate}')\n", encoding="utf-8",
                            )
                    result = subprocess.run(
                        ["bash", "-c", script], cwd=root, stdin=subprocess.DEVNULL,
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode == 0, expected,
                                     result.stdout + result.stderr)
                    if name == "empty":
                        self.assertIn("Missing Cline regression test cases", result.stderr)
                    if expected:
                        self.assertEqual(result.stderr.count("Ran 1 test"), len(groups))
                    else:
                        for later in groups[selected + 1:]:
                            self.assertNotIn("executed " + later, result.stdout)

    def legacy_required_steps(self):
        return (
            ("lint-and-audit", "Test Configuration Contracts", "tests/roo_contracts",
             "test_fixture.py", "test_*.py"),
            ("test-physical-mirror-install", "Test Asset Protection in Bounded Sequential Groups",
             "tests/roo_distribution", "test_asset_safety_fixture.py", "test_asset_safety*.py"),
            ("test-physical-mirror-install", "Test GitOps and Three IDE Layouts in Bounded Sequential Groups",
             "tests/roo_distribution", "test_gitops_fixture.py", "test_gitops*.py"),
            ("test-physical-mirror-install", "Test Suite Selection and Compatibility in Bounded Sequential Groups",
             "tests/roo_distribution", "test_suite_fixture.py", "test_suite*.py"),
            ("test-physical-mirror-install", "Test Deployment Guards in Bounded Sequential Groups",
             "tests/roo_distribution", "test_version_guard.py", "$group"),
            ("test-physical-mirror-install", "Test V4 Analysis Repair Distribution",
             "tests/roo_distribution", "test_v4_analysis_distribution.py",
             "test_v4_analysis_distribution.py"),
        )

    def test_legacy_required_steps_use_bounded_runner_without_filtering_tests(self):
        self.assertTrue((ROOT / "scripts/run-required-tests.py").is_file())
        for job, name, directory, filename, pattern in self.legacy_required_steps():
            with self.subTest(step=name):
                step = self.step(job, name)
                self.assertEqual(step["shell"], "bash")
                script = step["run"]
                for token in ("set -euo pipefail", "timeout --kill-after=2s 30s",
                              "python3 -B scripts/run-required-tests.py",
                              f"--directory {directory} --pattern", "< /dev/null"):
                    self.assertIn(token, script)
                self.assertNotIn("-m unittest discover", script)
                for forbidden in ("--exclude", "skip", "parallel", "xargs"):
                    self.assertNotIn(forbidden, script)
                # 拒绝后台运算符，但允许既有标准错误重定向 >&2。
                self.assertNotRegex(script, r"(?<![>&])&(?![>&])")
        configuration = self.step("lint-and-audit", "Test Configuration Contracts")["run"]
        self.assertIn("--pattern 'test_*.py'", configuration)
        # 历史 F3 测试仍在选择范围内；不删除或过滤既有退役／缺资产的跳过。
        self.assertTrue((ROOT / "tests/roo_contracts/test_f3_document_migration.py").is_file())

    def test_legacy_workflow_steps_reject_missing_empty_skipped_and_failed_files(self):
        passed = ("import unittest\nclass Case(unittest.TestCase):\n"
                  "    def test_required(self): self.assertTrue(True)\n")
        cases = (
            ("missing", None, False),
            ("empty", "import unittest\n", False),
            ("skip", "import unittest\nclass Case(unittest.TestCase):\n"
             "    @unittest.skip('required evidence unavailable')\n"
             "    def test_required(self): pass\n", False),
            ("failure", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_required(self): self.fail('injected failure')\n", False),
            ("import_skip", "import unittest\nraise unittest.SkipTest('retired fixture')\n", False),
            ("passed", passed, True),
        )
        for job, name, relative, filename, pattern in self.legacy_required_steps():
            script = self.step(job, name)["run"]
            for case, content, expected in cases:
                with self.subTest(step=name, case=case), tempfile.TemporaryDirectory(
                    prefix="sandbox-ci-legacy-required-", dir=Path(__file__).parent,
                ) as temporary:
                    root = Path(temporary)
                    directory = root / relative
                    directory.mkdir(parents=True)
                    scripts = root / "scripts"
                    scripts.mkdir()
                    (scripts / "run-required-tests.py").write_bytes(
                        (ROOT / "scripts/run-required-tests.py").read_bytes(),
                    )
                    if content is not None:
                        (directory / filename).write_text(content, encoding="utf-8")
                    if name == "Test Deployment Guards in Bounded Sequential Groups":
                        (directory / "test_task_cleanup_guard.py").write_text(
                            passed, encoding="utf-8",
                        )
                    result = subprocess.run(
                        ["bash", "-c", script], cwd=root, stdin=subprocess.DEVNULL,
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode == 0, expected,
                                     result.stdout + result.stderr)
                    if expected:
                        self.assertIn("Ran 1 test", result.stderr)
                    elif case != "missing":
                        self.assertIn("必需测试门禁拒绝", result.stderr)

    def test_runtime_evidence_boundary_remains_explicit(self):
        script = self.step(
            "test-physical-mirror-install", "State Verification Boundary"
        )["run"]
        self.assertIn("do not verify Roo runtime loading or permission enforcement", script)


if __name__ == "__main__":
    unittest.main()
