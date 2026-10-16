#!/usr/bin/env python3
"""类型化 unittest 子运行器；由监督器提供超时、单飞和完整日志。

只使用已准备的环境，不安装依赖。零命中、必需测试缺失、跳过和
预期失败均不能产生通过；本程序不提供测试代码的系统权限隔离。
"""
from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path
import sys
import unittest


class TestSelectionError(ValueError):
    """验证目标不满足显式选择契约。"""


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("最小测试数必须大于零")
    return number


def selected_directory(workspace: Path, relative: str) -> Path:
    root = workspace.resolve(strict=True)
    if not root.is_dir():
        raise TestSelectionError("任务工作区不是目录")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise TestSelectionError("测试目录必须位于任务工作区内")
    candidate = root
    for component in path.parts:
        candidate = candidate / component
        if candidate.is_symlink():
            raise TestSelectionError("测试目录路径不得通过软链接")
    directory = candidate.resolve(strict=True)
    if not directory.is_relative_to(root) or not directory.is_dir():
        raise TestSelectionError("测试目录不存在或越过任务工作区")
    return directory


def test_identifiers(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from test_identifiers(item)
        else:
            yield item.id()


def emit_result(result: dict) -> None:
    print("BMAD_TEST_RESULT " + json.dumps(
        result, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ), flush=True)


def run_tests(workspace: Path, directory: str, pattern: str,
              minimum_tests: int, required_tests: tuple[str, ...]) -> dict:
    if type(minimum_tests) is not int or minimum_tests < 1:
        raise TestSelectionError("最小测试数必须大于零")
    if (not isinstance(pattern, str) or not pattern
            or "/" in pattern or "\\" in pattern or "\x00" in pattern
            or not pattern.endswith(".py")):
        raise TestSelectionError("测试模式必须是单层 Python 文件匹配模式")
    if len(set(required_tests)) != len(required_tests):
        raise TestSelectionError("必需测试标识重复")
    if any(not isinstance(item, str) or not item.strip()
           or "\n" in item or "\r" in item for item in required_tests):
        raise TestSelectionError("必需测试标识非法")

    root = workspace.resolve(strict=True)
    target = selected_directory(root, directory)
    # 测试目录和工作区均为显式输入，不能从套件位置猜测任务源码根。
    sys.path.insert(0, str(root))
    loader = unittest.TestLoader()
    suite = loader.discover(str(target), pattern=pattern,
                            top_level_dir=str(target))
    identifiers = tuple(test_identifiers(suite))
    missing = sorted(set(required_tests) - set(identifiers))
    matched_files = sum(
        1 for path in target.rglob("*.py")
        if path.is_file() and fnmatch.fnmatch(path.name, pattern)
    )
    summary = {
        "workspace": str(root),
        "directory": directory,
        "pattern": pattern,
        "minimum_tests": minimum_tests,
        "discovered": len(identifiers),
        "matched_files": matched_files,
        "required_tests": list(required_tests),
        "missing_required_tests": missing,
        "tests_run": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "expected_failures": 0,
        "unexpected_successes": 0,
        "status": "BLOCKED",
        "reason": "",
    }
    if loader.errors:
        summary["reason"] = "测试发现失败"
        for error in loader.errors:
            print(error, file=sys.stderr)
        return summary
    if len(identifiers) < minimum_tests:
        summary["reason"] = "测试零命中或数量低于必需下限"
        return summary
    if len(set(identifiers)) != len(identifiers):
        summary["reason"] = "发现重复测试标识"
        return summary
    if missing:
        summary["reason"] = "必需测试未命中"
        return summary

    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    summary.update(
        tests_run=result.testsRun,
        failures=len(result.failures),
        errors=len(result.errors),
        skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures),
        unexpected_successes=len(result.unexpectedSuccesses),
    )
    if result.testsRun != len(identifiers):
        summary["reason"] = "发现与实际执行数量不一致"
    elif not result.wasSuccessful():
        summary["reason"] = "真实测试失败"
    elif result.skipped or result.expectedFailures:
        summary["reason"] = "必需验证存在跳过或预期失败"
    else:
        summary.update(status="PASS", reason="全部选中测试实际通过")
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--directory", required=True)
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--minimum-tests", type=positive_integer, default=1)
    parser.add_argument("--required-test", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        summary = run_tests(args.workspace, args.directory, args.pattern,
                            args.minimum_tests, tuple(args.required_test))
    except (OSError, ValueError, ImportError) as exc:
        emit_result({"status": "BLOCKED", "reason": str(exc),
                     "tests_run": 0})
        return 1
    emit_result(summary)
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
