#!/usr/bin/env python3
"""执行指定项目测试文件；缺文件、逐文件零收集、失败或跳过均拒绝。

仅作为必需测试的退出门禁，不过滤历史测试、不证明宿主加载或任务授权。
调用方负责串行、进程级超时、封闭输入和测试范围授权。
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest


DIRECTORIES = ("tests/roo_contracts", "tests/roo_distribution")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, choices=DIRECTORIES)
    parser.add_argument("--pattern", required=True, help="目录内测试文件名或 glob，不接受路径")
    arguments = parser.parse_args(argv)
    pattern = arguments.pattern
    if (not pattern.startswith("test_") or not pattern.endswith(".py")
            or any(character in pattern for character in ("/", "\\", "\x00"))):
        parser.error("测试模式必须是 test_ 开头、.py 结尾的目录内文件名或 glob")
    directory = Path(arguments.directory)
    try:
        for component in (directory.parent, directory):
            if component.is_symlink() or not component.is_dir():
                raise ValueError(f"必需测试目录缺失或不是物理目录：{component}")
        files = sorted(directory.glob(pattern))
        if not files:
            raise ValueError(f"缺少必需测试文件：{directory}/{pattern}")
        suites = []
        for path in files:
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"必需测试资产不是普通物理文件：{path}")
            suite = unittest.TestLoader().discover(str(directory), pattern=path.name)
            if suite.countTestCases() == 0:
                raise ValueError(f"必需测试文件零收集：{path}")
            suites.append((path, suite))
        for path, suite in suites:
            print(f"必需测试文件：{path}；收集 {suite.countTestCases()} 项", flush=True)
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            if not result.wasSuccessful() or result.skipped:
                print(f"必需测试门禁拒绝：{path}；失败、错误或跳过不能作为通过证据",
                      file=sys.stderr)
                return 1
        return 0
    except (OSError, ValueError, ImportError) as exc:
        print(f"必需测试门禁拒绝：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
