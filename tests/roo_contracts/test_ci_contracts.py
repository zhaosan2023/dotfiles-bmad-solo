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
                    if "unittest" in script:
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
                self.assertIn("timeout 30s python3", script)
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

    def test_runtime_evidence_boundary_remains_explicit(self):
        script = self.step(
            "test-physical-mirror-install", "State Verification Boundary"
        )["run"]
        self.assertIn("do not verify Roo runtime loading or permission enforcement", script)


if __name__ == "__main__":
    unittest.main()
