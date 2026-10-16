"""CI 静态配置回归；不执行网络安装、远程 CI 或真实宿主部署。"""
from pathlib import Path
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

    def test_static_gate_selects_both_versions_explicitly(self):
        script = self.step(
            "lint-and-audit",
            "Validate V4 and V5 Configuration and Metadata Contracts",
        )["run"]
        self.assertIn("set -euo pipefail", script)
        for suite in ("v4", "v5"):
            self.assertIn(
                "timeout 30s python3 -B scripts/validate-roo-contracts.py "
                f"--suite {suite} < /dev/null",
                script,
            )

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
                        self.assertIn("timeout 30s", script)
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

    def test_runtime_evidence_boundary_remains_explicit(self):
        script = self.step(
            "test-physical-mirror-install", "State Verification Boundary"
        )["run"]
        self.assertIn("do not verify Roo runtime loading or permission enforcement", script)


if __name__ == "__main__":
    unittest.main()
