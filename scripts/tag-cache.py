#!/usr/bin/env python3
"""按实际提交发布标签套件缓存；不修改分支，不部署资产。

旧标签命名缓存不自动接管。新缓存先在临时目录完整提取、核验，
再在同一父目录发布；已有缓存逐文件与提交归档核对，不静默修补。
"""
from __future__ import annotations

import argparse
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

from asset_safety import AssetError, Snapshot, checked_path, deployment_lock, snapshot
from deployment_source import collect_source
from managed_files import validate_relative_path


def git(repo, *arguments):
    environment = dict(os.environ)
    environment.update(GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    result = subprocess.run(
        ["git", "--no-pager", "-C", str(repo), *arguments],
        env=environment, stdin=subprocess.DEVNULL,
        capture_output=True, timeout=15,
    )
    if result.returncode:
        raise AssetError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def archive_files(repo, commit):
    content = git(repo, "archive", "--format=tar", commit, "bmad-suite-v4")
    files = {}
    directories = set()
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:") as archive:
        for member in archive:
            name = member.name.rstrip("/") if member.isdir() else member.name
            validate_relative_path(name)
            if name != "bmad-suite-v4" and not name.startswith("bmad-suite-v4/"):
                raise AssetError("归档包含套件范围外的路径")
            if name in files or name in directories:
                raise AssetError(f"归档路径重复：{name}")
            if member.isdir():
                directories.add(name)
                continue
            if not member.isfile() or member.mode & ~0o777:
                raise AssetError(f"归档包含链接、特殊文件或特殊权限：{name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise AssetError(f"无法读取归档成员：{name}")
            with stream:
                files[name] = Snapshot(stream.read(), member.mode)
    if not files:
        raise AssetError("提交缺少套件文件")
    for name in files:
        if any(parent.as_posix() in files for parent in Path(name).parents):
            raise AssetError(f"归档文件与父目录冲突：{name}")
    return files


def verify_cache(directory, commit, expected):
    directory = checked_path(directory)
    if not directory.is_dir():
        raise AssetError("缓存必须为物理目录")
    marker = snapshot(directory / "commit.txt")
    if marker != Snapshot((commit + "\n").encode("ascii"), 0o600):
        raise AssetError("缓存提交标识缺失或不匹配；保留现场并拒绝复用")
    actual = {}
    for parent, children, names in os.walk(directory, followlinks=False):
        for name in children:
            child = checked_path(Path(parent) / name)
            if not child.is_dir():
                raise AssetError(f"缓存包含非目录节点：{child}")
        for name in names:
            path = checked_path(Path(parent) / name)
            relative = path.relative_to(directory).as_posix()
            if relative != "commit.txt":
                actual[relative] = snapshot(path)
    if actual != expected:
        raise AssetError("缓存内容或权限与实际提交不符；拒绝复用不完整或被修改的缓存")
    # 包括必需资产、模式 YAML 和源链接边界校验。
    collect_source(directory / "bmad-suite-v4", ())


def prepare_cache(repo, tag):
    repo = checked_path(repo)
    git(repo, "check-ref-format", "refs/tags/" + tag)
    validate_relative_path(tag)
    commit = git(
        repo, "rev-parse", "--verify", "--end-of-options",
        "refs/tags/" + tag + "^{commit}",
    ).decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise AssetError("Git 返回了非法提交标识")
    cache_root = checked_path(repo / ".versions")
    legacy = checked_path(cache_root / tag)
    if legacy.exists():
        raise AssetError("发现旧标签命名缓存；需显式审核迁移，拒绝自动复用或覆盖")
    # 所有归档路径及类型先在内存中检查，不直接调用通用解包写入。
    expected = archive_files(repo, commit)
    cache_root.mkdir(mode=0o700, exist_ok=True)
    if not checked_path(cache_root).is_dir():
        raise AssetError("缓存根路径不是物理目录")
    with deployment_lock(cache_root / "cache.lock"):
        destination = checked_path(cache_root / ("commit-" + commit))
        if destination.exists():
            verify_cache(destination, commit, expected)
            return destination / "bmad-suite-v4"
        temporary = Path(tempfile.mkdtemp(prefix=".preparing-", dir=cache_root))
        try:
            for name, value in sorted(expected.items()):
                path = temporary / name
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with path.open("xb") as stream:
                    stream.write(value.content)
                    stream.flush()
                    os.fchmod(stream.fileno(), value.mode)
                    os.fsync(stream.fileno())
            marker = temporary / "commit.txt"
            with marker.open("xb") as stream:
                stream.write((commit + "\n").encode("ascii"))
                stream.flush()
                os.fchmod(stream.fileno(), 0o600)
                os.fsync(stream.fileno())
            verify_cache(temporary, commit, expected)
            if checked_path(destination).exists():
                raise AssetError("缓存发布目标意外出现，拒绝覆盖")
            temporary.rename(destination)
            return destination / "bmad-suite-v4"
        finally:
            # 仅清理本次创建的未发布临时目录；保留旧缓存和诊断现场。
            if temporary.exists():
                shutil.rmtree(temporary)


def main():
    parser = argparse.ArgumentParser(description="按提交核验并发布标签套件缓存")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--tag", required=True)
    arguments = parser.parse_args()
    try:
        print(prepare_cache(arguments.repo, arguments.tag))
        return 0
    except (AssetError, OSError, ValueError, tarfile.TarError,
            subprocess.TimeoutExpired) as exc:
        print(f"标签缓存未就绪：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
