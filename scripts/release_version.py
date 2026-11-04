#!/usr/bin/env python3
"""读取唯一发布版本并检查新发布契约；不改写旧套件身份或历史标签。"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from asset_safety import AssetError, checked_path, snapshot


ROOT = Path(__file__).resolve().parents[1]
RELEASE_PATTERN = re.compile(r"v4\.(?:0|[1-9][0-9]*)")
BADGE_PATTERN = re.compile(r"https://img\.shields\.io/badge/version-([^/]+)-blue\.svg")


def validate_release(version: str) -> str:
    """新发布仅使用 v4.数字；不把套件主身份或提交标识当作发布版本。"""
    if not isinstance(version, str) or RELEASE_PATTERN.fullmatch(version) is None:
        raise AssetError("发布版本须为 v4.数字，例如 v4.3；不接受补丁段或预发布后缀")
    return version


def parse_release(content: bytes) -> str:
    """解析已有快照字节；供源预检和部署诊断共用，不重新读取磁盘。"""
    if not isinstance(content, bytes):
        raise AssetError("VERSION 快照必须为字节")
    try:
        text = content.decode("ascii")
    except UnicodeError as exc:
        raise AssetError("VERSION 必须使用 ASCII 两段版本") from exc
    version = validate_release(text.removesuffix("\n"))
    if text != version + "\n":
        raise AssetError("VERSION 必须恰好包含一个版本及一个换行")
    return version


def read_release(source: Path, *, allow_legacy: bool = False) -> str:
    """读取已物化套件；仅明确允许的旧快照可缺 VERSION，损坏不降级。"""
    source = checked_path(source)
    if not source.is_dir():
        raise AssetError("版本来源必须是现有物理套件目录")
    value = snapshot(checked_path(source / "VERSION"))
    if value.content is None:
        if allow_legacy:
            return "v4"
        raise AssetError("当前套件缺少唯一发布版本文件 VERSION")
    return parse_release(value.content)


def check_repository(root: Path, *, tag: str | None = None) -> str:
    """校验当前发布来源、展示版本和可选新标签；不读取或修改 Git 引用。"""
    root = checked_path(root)
    version = read_release(root / "bmad-suite-v4")
    readme = snapshot(checked_path(root / "README.md"))
    if readme.content is None:
        raise AssetError("缺少当前发布说明 README.md")
    content = readme.content.decode("utf-8")
    if BADGE_PATTERN.findall(content) != [version]:
        raise AssetError("说明文档版本徽章必须与 VERSION 唯一对应")
    if "](bmad-suite-v4/VERSION)" not in content:
        raise AssetError("版本徽章须指向本地 VERSION，不预造未发布的远端标签")
    if tag is not None and validate_release(tag) != version:
        raise AssetError("新发布标签与 VERSION 不一致")
    return version


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    location = parser.add_mutually_exclusive_group()
    location.add_argument("--source", type=Path, help="只读取指定物理套件的发布版本")
    location.add_argument("--root", type=Path, help="检查指定仓库的发布一致性")
    parser.add_argument("--allow-legacy", action="store_true",
                        help="仅配合 --source：旧快照缺 VERSION 时只报告 v4")
    parser.add_argument("--tag", help="检查拟发布标签的两段格式及来源一致性")
    arguments = parser.parse_args(argv)
    if arguments.source is not None and arguments.tag is not None:
        parser.error("标签验收须检查整个仓库，不能只读取套件")
    if arguments.allow_legacy and arguments.source is None:
        parser.error("旧快照兼容仅允许用于显式 --source")
    try:
        if arguments.source is not None:
            version = read_release(arguments.source, allow_legacy=arguments.allow_legacy)
            if version == "v4":
                print("旧套件未声明发布小版本；仅报告主身份 v4，不推断 v4.3。", file=sys.stderr)
            print(version)
        else:
            version = check_repository(arguments.root or ROOT, tag=arguments.tag)
            print(f"PASS：发布版本 {version} 与说明文档及适用标签一致；未创建发布。")
        return 0
    except (AssetError, OSError, UnicodeError, ValueError) as exc:
        print(f"发布版本检查失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
