"""控制器反例的首批子运行器验证；不证明监督器、权限隔离或远程运行时。

每个用例在项目内临时工作区运行真实子进程，不安装依赖。
"""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


SUITE = Path(__file__).resolve().parents[1]
RUNNER = SUITE / "scripts/bmad_test_runner.py"
PREFIX = "BMAD_TEST_RESULT "


class TestRunnerGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-runner-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace with 'quote'"
        self.root.mkdir()
        self.tests = self.root / "tests"
        self.tests.mkdir()

    def fixture(self, body, name="test_sample.py"):
        path = self.tests / name
        path.write_text("import unittest\n\n" + body, encoding="utf-8")
        return path

    def run_runner(self, *arguments, directory="tests", pattern="test_*.py"):
        result = subprocess.run(
            [sys.executable, "-B", str(RUNNER),
             "--workspace", str(self.root), "--directory", directory,
             "--pattern", pattern, *arguments],
            cwd=self.root, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=5,
        )
        records = [line[len(PREFIX):] for line in result.stdout.splitlines()
                   if line.startswith(PREFIX)]
        self.assertEqual(len(records), 1, result.stdout + result.stderr)
        return result, json.loads(records[0])

    def assert_blocked(self, result, summary):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(summary["status"], "BLOCKED")

    def passing_fixture(self):
        self.fixture(
            "class Sample(unittest.TestCase):\n"
            "    def test_pass(self):\n"
            "        self.assertEqual(2 + 2, 4)\n"
        )

    def test_actual_success_has_matching_execution_counts(self):
        self.passing_fixture()
        result, summary = self.run_runner(
            "--required-test", "test_sample.Sample.test_pass"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["workspace"], str(self.root.resolve()))
        self.assertEqual(summary["discovered"], 1)
        self.assertEqual(summary["tests_run"], 1)
        self.assertEqual(summary["matched_files"], 1)
        self.assertEqual(summary["missing_required_tests"], [])

    def test_real_assertion_failure_is_not_log_success(self):
        self.fixture(
            "class Sample(unittest.TestCase):\n"
            "    def test_failure(self):\n"
            "        self.assertEqual(1, 2, 'actual assertion failure')\n"
        )
        result, summary = self.run_runner()
        self.assert_blocked(result, summary)
        self.assertEqual(summary["tests_run"], 1)
        self.assertEqual(summary["failures"], 1)
        self.assertIn("actual assertion failure", result.stderr)

    def test_zero_discovery_blocks(self):
        result, summary = self.run_runner()
        self.assert_blocked(result, summary)
        self.assertEqual(summary["discovered"], 0)
        self.assertEqual(summary["tests_run"], 0)

    def test_below_minimum_blocks_before_tests_execute(self):
        self.passing_fixture()
        result, summary = self.run_runner("--minimum-tests", "2")
        self.assert_blocked(result, summary)
        self.assertEqual(summary["tests_run"], 0)

    def test_missing_required_identifier_blocks_before_execution(self):
        self.passing_fixture()
        result, summary = self.run_runner(
            "--required-test", "test_sample.Sample.test_missing"
        )
        self.assert_blocked(result, summary)
        self.assertEqual(summary["tests_run"], 0)
        self.assertEqual(summary["missing_required_tests"],
                         ["test_sample.Sample.test_missing"])

    def test_skipped_test_is_not_pass(self):
        self.fixture(
            "class Sample(unittest.TestCase):\n"
            "    @unittest.skip('required dependency absent')\n"
            "    def test_skipped(self):\n"
            "        self.fail('must not run')\n"
        )
        result, summary = self.run_runner()
        self.assert_blocked(result, summary)
        self.assertEqual(summary["skipped"], 1)

    def test_expected_failure_is_not_pass(self):
        self.fixture(
            "class Sample(unittest.TestCase):\n"
            "    @unittest.expectedFailure\n"
            "    def test_known_failure(self):\n"
            "        self.fail('known failure remains')\n"
        )
        result, summary = self.run_runner()
        self.assert_blocked(result, summary)
        self.assertEqual(summary["expected_failures"], 1)

    def test_unexpected_success_is_not_pass(self):
        self.fixture(
            "class Sample(unittest.TestCase):\n"
            "    @unittest.expectedFailure\n"
            "    def test_unexpected_pass(self):\n"
            "        self.assertTrue(True)\n"
        )
        result, summary = self.run_runner()
        self.assert_blocked(result, summary)
        self.assertEqual(summary["unexpected_successes"], 1)

    def test_import_failure_blocks(self):
        self.fixture("raise ImportError('injected missing dependency')\n")
        result, summary = self.run_runner()
        self.assert_blocked(result, summary)
        self.assertIn("injected missing dependency", result.stderr)
        self.assertEqual(summary["tests_run"], 0)

    def test_duplicate_discovered_identifiers_block(self):
        self.passing_fixture()
        with (self.tests / "test_sample.py").open("a", encoding="utf-8") as file:
            file.write(
                "\ndef load_tests(loader, tests, pattern):\n"
                "    return unittest.TestSuite([\n"
                "        Sample('test_pass'), Sample('test_pass')])\n"
            )
        result, summary = self.run_runner()
        self.assert_blocked(result, summary)
        self.assertIn("重复测试标识", summary["reason"])
        self.assertEqual(summary["tests_run"], 0)

    def test_duplicate_required_identifiers_block(self):
        self.passing_fixture()
        identifier = "test_sample.Sample.test_pass"
        result, summary = self.run_runner(
            "--required-test", identifier, "--required-test", identifier
        )
        self.assert_blocked(result, summary)
        self.assertIn("重复", summary["reason"])

    def test_directory_escape_absolute_and_symlink_are_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.tests, target_is_directory=True)
        for directory in ("../", str(self.tests), "alias"):
            with self.subTest(directory=directory):
                result, summary = self.run_runner(directory=directory)
                self.assert_blocked(result, summary)
                self.assertEqual(summary["tests_run"], 0)

    def test_path_patterns_are_rejected(self):
        for pattern in ("../test_*.py", "nested/test_*.py", "test_*.txt"):
            with self.subTest(pattern=pattern):
                result, summary = self.run_runner(pattern=pattern)
                self.assert_blocked(result, summary)

    def test_fixture_changes_require_a_new_actual_execution(self):
        self.passing_fixture()
        first, summary = self.run_runner()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(summary["status"], "PASS")
        self.fixture(
            "class Sample(unittest.TestCase):\n"
            "    def test_pass(self):\n"
            "        self.fail('modified test now fails')\n"
        )
        second, summary = self.run_runner()
        self.assert_blocked(second, summary)
        self.assertEqual(summary["failures"], 1)


if __name__ == "__main__":
    unittest.main()
