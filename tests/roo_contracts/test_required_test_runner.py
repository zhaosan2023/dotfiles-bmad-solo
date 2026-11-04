"""必需测试门禁的项目内隔离负控；不运行业务测试或真实宿主。"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/run-required-tests.py"
PASS = "import unittest\nclass Case(unittest.TestCase):\n    def test_required(self): self.assertTrue(True)\n"
SKIP = "import unittest\nclass Case(unittest.TestCase):\n    @unittest.skip('required evidence unavailable')\n    def test_required(self): pass\n"


class RequiredTestRunner(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="sandbox-required-runner-", dir=Path(__file__).parent,
        )
        self.root = Path(self.temporary.name)
        self.directory = self.root / "tests/roo_contracts"
        self.directory.mkdir(parents=True)

        def cleanup():
            self.temporary.cleanup()
            self.assertFalse(self.root.exists(), "隔离夹具必须清理完成")
        self.addCleanup(cleanup)

    def write(self, name, content):
        path = self.directory / name
        path.write_text(content, encoding="utf-8")
        return path

    def run_gate(self, pattern="test_*.py", directory="tests/roo_contracts"):
        return subprocess.run(
            [sys.executable, "-B", str(RUNNER), "--directory", directory,
             "--pattern", pattern], cwd=self.root, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_missing_empty_failed_skipped_and_import_faults_are_rejected(self):
        cases = (
            ("missing", None, "缺少必需测试文件"),
            ("empty", "import unittest\n", "零收集"),
            ("failure", "import unittest\nclass Case(unittest.TestCase):\n"
             "    def test_required(self): self.fail('injected failure')\n", "injected failure"),
            ("skip", SKIP, "required evidence unavailable"),
            ("mixed_skip", PASS + "    @unittest.skip('required evidence unavailable')\n"
             "    def test_other(self): pass\n", "required evidence unavailable"),
            ("import_error", "raise RuntimeError('injected import error')\n", "injected import error"),
            ("import_skip", "import unittest\nraise unittest.SkipTest('retired fixture')\n",
             "retired fixture"),
        )
        for name, content, diagnostic in cases:
            with self.subTest(case=name):
                filename = "test_" + name + ".py"
                if content is not None:
                    self.write(filename, content)
                result = self.run_gate(filename)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(diagnostic, result.stdout + result.stderr)
                self.assertIn("必需测试门禁拒绝", result.stderr)

    def test_positive_multiple_files_are_collected_and_run_serially(self):
        for filename in ("test_b.py", "test_a.py"):
            self.write(filename, PASS + f"print('loaded {filename}')\n")
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr.count("Ran 1 test"), 2)
        self.assertLess(result.stdout.index("必需测试文件：tests/roo_contracts/test_a.py"),
                        result.stdout.index("必需测试文件：tests/roo_contracts/test_b.py"))

    def test_empty_file_cannot_hide_behind_nonempty_peer(self):
        self.write("test_a.py", PASS)
        self.write("test_b.py", "import unittest\n")
        result = self.run_gate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("test_b.py", result.stderr)
        self.assertIn("零收集", result.stderr)
        self.assertNotIn("Ran 1 test", result.stderr)

    def test_failure_stops_execution_of_later_file(self):
        self.write("test_a.py", SKIP)
        self.write("test_b.py", "import unittest\nclass Case(unittest.TestCase):\n"
                   "    def test_required(self):\n"
                   "        from pathlib import Path\n"
                   "        Path('must-not-exist').write_text('later test ran')\n")
        result = self.run_gate()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "must-not-exist").exists())
        self.assertNotIn("必需测试文件：tests/roo_contracts/test_b.py", result.stdout)

    def test_missing_directory_and_unsupported_paths_are_rejected(self):
        for directory in ("tests/roo_distribution", "../tests/roo_contracts"):
            with self.subTest(directory=directory):
                result = self.run_gate(directory=directory)
                self.assertNotEqual(result.returncode, 0)
        for pattern in ("../test_escape.py", "test_x/other.py", "test_x\\other.py", "*.py"):
            with self.subTest(pattern=pattern):
                self.assertNotEqual(self.run_gate(pattern).returncode, 0)

    def test_linked_directory_and_file_are_rejected_without_consuming_target(self):
        protected = self.root / "protected.py"
        protected.write_text("raise RuntimeError('must not import')\n", encoding="utf-8")
        link = self.directory / "test_link.py"
        link.symlink_to(protected)
        result = self.run_gate("test_link.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("不是普通物理文件", result.stderr)
        self.assertNotIn("must not import", result.stderr)
        link.unlink()
        self.directory.rmdir()
        self.directory.symlink_to(self.root, target_is_directory=True)
        result = self.run_gate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("不是物理目录", result.stderr)
        self.assertEqual(protected.read_text(), "raise RuntimeError('must not import')\n")

    def test_distribution_directory_is_supported_without_source_mutation(self):
        directory = self.root / "tests/roo_distribution"
        directory.mkdir()
        path = directory / "test_fixture.py"
        path.write_text(PASS, encoding="utf-8")
        before = path.read_bytes()
        result = self.run_gate("test_fixture.py", "tests/roo_distribution")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(list(self.root.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
